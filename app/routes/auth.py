from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app.services import log_action

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            log_action('LOGIN', 'user', user.id)
            return redirect(url_for('main.index'))
        flash('Ulanyjy ady ýa-da açar sözi nädogry', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_action('LOGOUT', 'user', current_user.id)
    logout_user()
    return redirect(url_for('auth.login'))
