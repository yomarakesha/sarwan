from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Subscriber, Phone, Order, Payment
from app.services import log_action

subscribers_bp = Blueprint('subscribers', __name__)

@subscribers_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    search_type = request.args.get('type', 'phone')  # phone, name, address, all
    
    query = Subscriber.query
    
    if search:
        if search_type == 'phone':
            query = query.join(Phone).filter(Phone.number.ilike(f'%{search}%'))
        elif search_type == 'address':
            query = query.filter(Subscriber.address.ilike(f'%{search}%'))
        else:
            query = query.outerjoin(Phone).filter(
                db.or_(
                    Phone.number.ilike(f'%{search}%'),
                    Subscriber.address.ilike(f'%{search}%')
                )
            ).distinct()
    
    subscribers = query.order_by(Subscriber.id.desc()).all()
    
    # Calculate credit for each subscriber (total_amount - paid_amount from all orders)
    subscriber_credits = {}
    for s in subscribers:
        total_orders = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.subscriber_id == s.id
        ).scalar() or 0
        total_order_paid = db.session.query(db.func.sum(Order.paid_amount)).filter(
            Order.subscriber_id == s.id
        ).scalar() or 0
        total_direct_paid = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.subscriber_id == s.id
        ).scalar() or 0
        subscriber_credits[s.id] = float(total_orders) - (float(total_order_paid) + float(total_direct_paid))
    
    return render_template('subscribers.html', subscribers=subscribers, search=search, 
                          search_type=search_type, subscriber_credits=subscriber_credits)

@subscribers_bp.route('/create', methods=['POST'])
@login_required
def create():
    client_type = request.form.get('client_type')
    address = request.form.get('address')
    phones = request.form.getlist('phones[]')
    
    subscriber = Subscriber(
        client_type=client_type,
        address=address
    )
    
    # Promo Fields
    promo_start = request.form.get('promo_start_date')
    if promo_start:
        try:
            from datetime import datetime
            subscriber.promo_start_date = datetime.strptime(promo_start, '%Y-%m-%d')
        except ValueError:
            pass # Ignore invalid date
            
    db.session.add(subscriber)
    db.session.flush()
    
    for phone in phones:
        if phone.strip():
            p = Phone(subscriber_id=subscriber.id, number=phone.strip())
            db.session.add(p)
    
    db.session.commit()
    log_action('CREATE', 'subscriber', subscriber.id, {
        'client_type': client_type,
        'address': address
    })
    flash('Müşderi döredildi', 'success')
    return redirect(url_for('subscribers.index'))

@subscribers_bp.route('/<int:id>/edit', methods=['POST'])
@login_required
def edit(id):
    subscriber = Subscriber.query.get_or_404(id)
    
    subscriber.client_type = request.form.get('client_type')
    subscriber.address = request.form.get('address', '')
    
    # Promo Fields Update
    promo_start = request.form.get('promo_start_date')
    if promo_start:
        try:
            from datetime import datetime
            subscriber.promo_start_date = datetime.strptime(promo_start, '%Y-%m-%d')
        except ValueError:
            pass
    else:
        subscriber.promo_start_date = None # Clear if empty
        
    # Update phones
    Phone.query.filter_by(subscriber_id=id).delete()
    phones = request.form.getlist('phones[]')
    for phone in phones:
        if phone.strip():
            p = Phone(subscriber_id=id, number=phone.strip())
            db.session.add(p)
    
    db.session.commit()
    log_action('UPDATE', 'subscriber', id, {'updated': 'details'}) # Removed full_name ref
    flash('Müşderi täzelendi', 'success')
    return redirect(url_for('subscribers.index'))

@subscribers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    subscriber = Subscriber.query.get_or_404(id)
    
    # Delete all associated orders first
    orders_deleted = Order.query.filter_by(subscriber_id=id).delete()
    
    # Delete all associated payments
    payments_deleted = Payment.query.filter_by(subscriber_id=id).delete()
    
    db.session.delete(subscriber)
    db.session.commit()
    log_action('DELETE', 'subscriber', id, {
        'orders_deleted': orders_deleted,
        'payments_deleted': payments_deleted
    })
    flash('Müşderi öçürildi', 'success')
    return redirect(url_for('subscribers.index'))

@subscribers_bp.route('/<int:id>/json')
@login_required
def get_json(id):
    subscriber = Subscriber.query.get_or_404(id)
    if not subscriber:
        return jsonify({'error': 'Not found'}), 404
    
    # Check promo status
    from app.services.pricing import get_promo_water_price
    from app.models import Settings, Order
    
    promo_price = get_promo_water_price(id)
    is_promo = promo_price is not None
    
    # Get limit for display
    promo_limit_setting = Settings.query.get('promo_water_limit')
    limit = int(promo_limit_setting.value) if promo_limit_setting else 10
    
    order_count = Order.query.filter_by(subscriber_id=id).count()

    return jsonify({
        'id': subscriber.id,
        'client_type': subscriber.client_type,
        'address': subscriber.address,
        'debt': float(subscriber.debt),
        'phones': [p.number for p in subscriber.phones],
        'promo': {
            'is_active': is_promo,
            'price': float(promo_price) if promo_price else 15.0, # Approximate standard
            'limit': limit,
            'count': order_count
        }
    })
