from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User, Price, ActionLog, Settings
from app.services import log_action

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Diňe dolandyryjy üçin', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.order_by(User.id).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role', 'user')
    
    if User.query.filter_by(username=username).first():
        flash('Bu ulanyjy ady eýýäm bar', 'error')
        return redirect(url_for('admin.users'))
    
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    log_action('CREATE', 'user', user.id, {'username': username, 'role': role})
    flash('Ulanyjy döredildi', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    user.username = request.form.get('username')
    user.role = request.form.get('role')
    
    password = request.form.get('password')
    if password:
        user.set_password(password)
    
    db.session.commit()
    log_action('UPDATE', 'user', id, {'username': user.username})
    flash('Ulanyjy täzelendi', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    if id == current_user.id:
        flash('Özüňizi öçürip bilmeýärsiňiz', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    log_action('DELETE', 'user', id)
    flash('Ulanyjy öçürildi', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/prices')
@login_required
@admin_required
def prices():
    prices = Price.query.all()
    if not prices:
        # Seed default prices
        defaults = [
            ('new_bottle', 101, 105),
            ('exchange', 61, 65),
            ('water_only', 11, 15)
        ]
        for op, legal, individual in defaults:
            p = Price(operation_type=op, legal_price=legal, individual_price=individual)
            db.session.add(p)
        db.session.commit()
        prices = Price.query.all()
    
    return render_template('admin/prices.html', prices=prices)

@admin_bp.route('/prices/update', methods=['POST'])
@login_required
@admin_required
def update_prices():
    for price in Price.query.all():
        legal = request.form.get(f'legal_{price.id}', type=float)
        individual = request.form.get(f'individual_{price.id}', type=float)
        if legal is not None:
            price.legal_price = Decimal(str(legal))
        if individual is not None:
            price.individual_price = Decimal(str(individual))
    
    db.session.commit()
    log_action('UPDATE', 'prices', None, {'updated': 'all'})
    flash('Bahalar täzelendi', 'success')
    return redirect(url_for('admin.prices'))

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    logs = ActionLog.query.order_by(ActionLog.created_at.desc()).paginate(page=page, per_page=50)
    return render_template('admin/logs.html', logs=logs)

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    # Fetch all settings
    settings_list = Settings.query.all()
    # Convert list to dict for easier access if needed, or just pass list
    # Let's pass a dict for easier template access: settings.promo_water_price
    settings_dict = {s.key: s for s in settings_list}
    return render_template('admin/settings.html', settings=settings_dict)

@admin_bp.route('/settings/update', methods=['POST'])
@login_required
@admin_required
def update_settings():
    # Promo settings update logic removed

        
    db.session.commit()
    log_action('UPDATE', 'settings', None, {'updated': 'promo_settings'})
    flash('Sazlamalar täzelendi', 'success')
    return redirect(url_for('admin.settings'))
