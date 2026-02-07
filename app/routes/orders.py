from decimal import Decimal
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Order, Subscriber, Price, Payment
from app.services import log_action

orders_bp = Blueprint('orders', __name__)

def calculate_order_total(subscriber, new_bottles, exchange_bottles, water_only):
    """Calculate total based on client type and prices"""
    prices = {p.operation_type: p for p in Price.query.all()}
    
    if subscriber.client_type == 'legal':
        new_price = prices.get('new_bottle', Price(legal_price=101)).legal_price
        exchange_price = prices.get('exchange', Price(legal_price=61)).legal_price
        water_price = prices.get('water_only', Price(legal_price=11)).legal_price
    else:
        new_price = prices.get('new_bottle', Price(individual_price=105)).individual_price
        exchange_price = prices.get('exchange', Price(individual_price=65)).individual_price
        water_price = prices.get('water_only', Price(individual_price=15)).individual_price
    
    total = (Decimal(new_bottles) * new_price + 
             Decimal(exchange_bottles) * exchange_price + 
             Decimal(water_only) * water_price)
    return total

def recalculate_debt(subscriber):
    """Recalculate subscriber debt from orders and payments"""
    total_orders = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.subscriber_id == subscriber.id
    ).scalar() or 0
    
    total_payments = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.subscriber_id == subscriber.id
    ).scalar() or 0
    
    subscriber.debt = Decimal(total_orders) - Decimal(total_payments)
    db.session.commit()

@orders_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    search_type = request.args.get('type', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = Order.query.join(Subscriber)
    
    if search:
        if search_type == 'id':
            query = query.filter(Order.id == int(search) if search.isdigit() else -1)
        elif search_type == 'address':
            query = query.filter(Subscriber.address.ilike(f'%{search}%'))
        else:
            query = query.filter(
                db.or_(
                    Subscriber.address.ilike(f'%{search}%'),
                    Order.id == (int(search) if search.isdigit() else -1)
                )
            )
    
    if date_from:
        query = query.filter(Order.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Order.created_at <= datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
    
    orders = query.order_by(Order.id.desc()).all()
    subscribers = Subscriber.query.order_by(Subscriber.full_name).all()
    prices = {p.operation_type: p for p in Price.query.all()}
    
    # Calculate total bottles for each subscriber
    subscriber_bottles = {}
    for s in subscribers:
        total_new = db.session.query(db.func.sum(Order.new_bottles)).filter(
            Order.subscriber_id == s.id
        ).scalar() or 0
        total_exchange = db.session.query(db.func.sum(Order.exchange_bottles)).filter(
            Order.subscriber_id == s.id
        ).scalar() or 0
        total_free = db.session.query(db.func.sum(Order.free_bottles)).filter(
            Order.subscriber_id == s.id
        ).scalar() or 0
        subscriber_bottles[s.id] = total_new + total_exchange + total_free
    
    return render_template('orders.html', orders=orders, subscribers=subscribers, prices=prices,
                          search=search, search_type=search_type, date_from=date_from, date_to=date_to,
                          subscriber_bottles=subscriber_bottles)

@orders_bp.route('/create', methods=['POST'])
@login_required
def create():
    subscriber_id = request.form.get('subscriber_id', type=int)
    # Standard fields
    new_bottles = request.form.get('new_bottles', 0, type=int)
    exchange_bottles = request.form.get('exchange_bottles', 0, type=int)
    water_only = request.form.get('water_only', 0, type=int)
    free_bottles = request.form.get('free_bottles', 0, type=int)
    
    # Credit fields
    gap_bilen = request.form.get('gap_bilen', 0, type=int)  # Gap bilen × 105 TMT
    dine_suw = request.form.get('dine_suw', 0, type=int)    # Diňe suw × 15 TMT
    
    paid_amount = request.form.get('paid_amount', type=float)
    is_free = request.form.get('is_free') == 'on'
    
    subscriber = Subscriber.query.get_or_404(subscriber_id)
    
    # Determine mode: if Credit fields are > 0, use Credit logic
    # (Check if standard fields are 0 to be safe, or just prioritize Credit?)
    # Let's check if credit fields are used
    if gap_bilen > 0 or dine_suw > 0:
        # Credit Mode: Prices 105/15, Payment is 0 unless Mugt
        total = Decimal(gap_bilen * 105 + dine_suw * 15)
        # Map credit fields to db fields
        # gap_bilen -> new_bottles (assuming buying bottle)
        # dine_suw -> exchange_bottles (assuming just water)
        # But wait, standard logic:
        # new_bottles = bottle + water
        # exchange_bottles = just water (but bringing bottle)
        # water_only = just water (no bottle exchange?) - DB says water_only price 15(ind)/11(leg).
        # exchange price: 65(ind)/61(leg).
        # Ah, "Dine suw x 15" implies standard water price.
        # "Gap bilen x 105" implies standard new bottle price.
        
        # Override counts for DB
        new_bottles = gap_bilen
        # dine_suw (15 TMT) maps to water_only price (15 TMT). 
        # But 'exchange_bottles' usually costs 65 TMT (includes service/exchange?).
        # 'water_only' price is 15 TMT. So dine_suw -> water_only.
        water_only = dine_suw
        # Reset others
        exchange_bottles = 0
        free_bottles = 0
        
        # Credit implies taking debt, so paid is 0
        paid = Decimal('0')
        
    else:
        # Standard Mode
        total = calculate_order_total(subscriber, new_bottles, exchange_bottles, water_only)
        
        # If paid_amount not specified, assume full payment
        if paid_amount is None:
            paid = Decimal(str(float(total)))
        else:
            paid = Decimal(str(paid_amount))

    # Free Order override
    if is_free:
        total = Decimal('0')
        paid = Decimal('0')
    
    order = Order(
        subscriber_id=subscriber_id,
        user_id=current_user.id,
        new_bottles=new_bottles,
        exchange_bottles=exchange_bottles,
        water_only=water_only,
        free_bottles=free_bottles,
        total_amount=total,
        paid_amount=paid,
        is_free=is_free
    )
    db.session.add(order)
    db.session.commit()
    
    recalculate_debt(subscriber)
    log_action('CREATE', 'order', order.id, {
        'subscriber_id': subscriber_id,
        'new_bottles': new_bottles,
        'exchange_bottles': exchange_bottles,
        'water_only': water_only,
        'total': float(total),
        'paid': float(paid),
        'is_free': is_free
    })
    
    flash('Sargyt döredildi', 'success')
    return redirect(url_for('orders.index'))

@orders_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    order = Order.query.get_or_404(id)
    subscriber = order.subscriber
    db.session.delete(order)
    db.session.commit()
    recalculate_debt(subscriber)
    log_action('DELETE', 'order', id)
    flash('Sargyt öçürildi', 'success')
    return redirect(url_for('orders.index'))

@orders_bp.route('/payment', methods=['POST'])
@login_required
def add_payment():
    subscriber_id = request.form.get('subscriber_id', type=int)
    amount = request.form.get('amount', type=float)
    
    payment = Payment(
        subscriber_id=subscriber_id,
        user_id=current_user.id,
        amount=Decimal(str(amount))
    )
    db.session.add(payment)
    db.session.commit()
    
    subscriber = Subscriber.query.get(subscriber_id)
    recalculate_debt(subscriber)
    log_action('CREATE', 'payment', payment.id, {'subscriber_id': subscriber_id, 'amount': amount})
    
    flash('Töleg goşuldy', 'success')
    return redirect(url_for('subscribers.index'))
