from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin or user
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    logs = db.relationship('ActionLog', backref='user', lazy='dynamic')
    orders = db.relationship('Order', backref='created_by', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Subscriber(db.Model):
    __tablename__ = 'subscribers'
    id = db.Column(db.Integer, primary_key=True)
    client_type = db.Column(db.String(20), nullable=False)  # Magazinlar (legal) or Rayat (individual)
    address = db.Column(db.String(256), nullable=True)  # Subscriber address
    debt = db.Column(db.Numeric(12, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Promo Control
    promo_start_date = db.Column(db.DateTime, nullable=True) # If set, only count orders after this date
    promo_custom_limit = db.Column(db.Integer, nullable=True) # If set, override global limit
    
    phones = db.relationship('Phone', backref='subscriber', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='subscriber', lazy='dynamic')
    payments = db.relationship('Payment', backref='subscriber', lazy='dynamic')

class Phone(db.Model):
    __tablename__ = 'phones'
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscribers.id'), nullable=False)
    number = db.Column(db.String(20), nullable=False)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscribers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    new_bottles = db.Column(db.Integer, default=0)      # Täze çüýşe
    exchange_bottles = db.Column(db.Integer, default=0)  # Çalyşyk
    water_only = db.Column(db.Integer, default=0)        # Diňe suw
    free_bottles = db.Column(db.Integer, default=0)      # Mugt goýlan harytlar
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), default=0)  # Tölenen mukdar (kredit = total - paid)
    is_free = db.Column(db.Boolean, default=False)  # Mugt sargyt
    created_at = db.Column(db.DateTime, default=datetime.now)

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscribers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Price(db.Model):
    __tablename__ = 'prices'
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.String(32), unique=True, nullable=False)
    legal_price = db.Column(db.Numeric(10, 2), nullable=False)
    individual_price = db.Column(db.Numeric(10, 2), nullable=False)

class ActionLog(db.Model):
    __tablename__ = 'action_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(64), nullable=False)
    entity = db.Column(db.String(64))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Settings(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(256))
    description = db.Column(db.String(256))
