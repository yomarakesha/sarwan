from decimal import Decimal
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Order, Subscriber, Price, Payment
from app.services import log_action
from app.services.pricing import get_promo_water_price

orders_bp = Blueprint('orders', __name__)

def calculate_order_total(subscriber, new_bottles, exchange_bottles, water_only, free_bottles):
    """Calculate total based on client type and prices"""
    prices = {p.operation_type: p for p in Price.query.all()}
    
    # Defaults based on new requirements:
    # Water: 15
    # Container: 90
    # New Bottle (Water+Container): 105
    # Exchange: 50
    # "Goýup bermek" -> Container Only: 90
    
    if subscriber.client_type == 'legal':
        # Magazinlar prices (Adjust if legal prices differ, for now using same or existing logic if present)
        # Using existing pattern but updating defaults if missing
        new_price = prices.get('new_bottle', Price(legal_price=105)).legal_price
        exchange_price = prices.get('exchange', Price(legal_price=50)).legal_price
        water_price = prices.get('water_only', Price(legal_price=15)).legal_price
        container_price = prices.get('container', Price(legal_price=90)).legal_price
    else:
        # Rayat prices
        new_price = prices.get('new_bottle', Price(individual_price=105)).individual_price
        exchange_price = prices.get('exchange', Price(individual_price=50)).individual_price
        water_price = prices.get('water_only', Price(individual_price=15)).individual_price
        container_price = prices.get('container', Price(individual_price=90)).individual_price
    
    # Check for promo price for water_only
    # Check for promo price for water_only and others
    promo_price = get_promo_water_price(subscriber.id)
    if promo_price is not None:
        # Calculate discount delta (Standard - Promo)
        # Assuming Standard is the price we just fetched for water_only? 
        # Actually, water_price above is the specific price for this client type (15 or 11).
        # PROMO is fixed at 10.
        # If Client Type is legal (11 TMT), promo (10) is 1 TMT off.
        # If Client Type is individual (15 TMT), promo (10) is 5 TMT off.
        
        # Apply promo directly to water_only
        delta = water_price - promo_price
        
        # Apply same delta to other water-containing products
        # Ensure we don't go below 0 or break logic if delta is negative (unlikely unless promo > standard)
        if delta > 0:
            water_price = promo_price # Set water to promo
            new_price = new_price - delta
            exchange_price = exchange_price - delta

    total = (Decimal(new_bottles) * new_price + 
             Decimal(exchange_bottles) * exchange_price + 
             Decimal(water_only) * water_price +
             Decimal(free_bottles) * container_price)
    return total

def recalculate_debt(subscriber):
    """Recalculate subscriber debt from orders and payments"""
    total_orders = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.subscriber_id == subscriber.id
    ).scalar() or 0
    
    total_order_payments = db.session.query(db.func.sum(Order.paid_amount)).filter(
        Order.subscriber_id == subscriber.id
    ).scalar() or 0
    
    total_direct_payments = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.subscriber_id == subscriber.id
    ).scalar() or 0
    
    subscriber.debt = Decimal(total_orders) - (Decimal(total_order_payments) + Decimal(total_direct_payments))
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
    subscribers = Subscriber.query.order_by(Subscriber.id.desc()).all()
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
        # Credit Mode: Prices 105/15 (or promo)
        
        # Determine water price (15 or 10)
        water_price = Decimal('15.00')
        promo_price = get_promo_water_price(subscriber.id)
        if promo_price is not None:
            water_price = promo_price
            # Also apply discount to New Bottle (Gap bilen)
            # Standard Gap Bilen is 105. 
            # If promo applies (10 vs 15), delta is 5.
            # So Gap Bilen becomes 100.
            # But wait, credit mode logic below calculates total manually:
            # total = Decimal(gap_bilen * 105 + dine_suw * water_price)
            # We need to adjust the 105 constant too if promo active.
            pass # Logic handled below
            
        # Calculate totals with potential promo
        gap_bilen_price = Decimal('105.00')
        if promo_price is not None:
             # Apply 5 TMT discount to new bottle too (105 -> 100)
             # Assumption: Standard water is 15. Promo is 10. Delta 5.
             gap_bilen_price = Decimal('100.00')
             
        total = Decimal(gap_bilen) * gap_bilen_price + Decimal(dine_suw) * water_price
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
        total = calculate_order_total(subscriber, new_bottles, exchange_bottles, water_only, free_bottles)
        
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
    
    if current_user.role not in ['admin', 'accountant']:
        flash('Diňe hasapçy töleg kabul edip bilýär!', 'danger')
        return redirect(url_for('subscribers.index'))

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
