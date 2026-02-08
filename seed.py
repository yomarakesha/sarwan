"""Seed script to create initial data and mock data for testing"""
from decimal import Decimal
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Price, Subscriber, Phone, Order, Payment

def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        
        # Create admin user
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print("Admin: admin / admin123")
        
        # Create accountant user
        if not User.query.filter_by(username='accountant').first():
            acc = User(username='accountant', role='accountant')
            acc.set_password('acc123')
            db.session.add(acc)
            print("Accountant: accountant / acc123")
        
        # Create test user (operator)
        if not User.query.filter_by(username='operator').first():
            user = User(username='operator', role='user')
            user.set_password('operator123')
            db.session.add(user)
            print("User: operator / operator123")
        
        # Create prices
        if not Price.query.first():
            prices = [
                Price(operation_type='new_bottle', legal_price=105, individual_price=105),
                Price(operation_type='exchange', legal_price=50, individual_price=50),
                Price(operation_type='water_only', legal_price=15, individual_price=15),
                Price(operation_type='container', legal_price=90, individual_price=90),
            ]
            db.session.add_all(prices)
            db.session.add_all(prices)
            print("Prices created")

        # Create settings
        from app.models import Settings
        if not Settings.query.first():
            settings = [
                Settings(key='promo_water_price', value='10', description='Promotional price for water (first 10 orders)'),
                Settings(key='promo_water_limit', value='10', description='Order count limit for promo price'),
            ]
            db.session.add_all(settings)
            print("Settings created")
        
        db.session.commit()
        
        # Create mock subscribers (Address, Client Type, Phones)
        if not Subscriber.query.first():
            subscribers_data = [
                ('legal', 'Bitarap köçe, jaý 15', ['+99361123456']),
                ('individual', 'Magtymguly şaýoly, jaý 42', ['+99365987654', '+99362111222']),
                ('individual', 'Andalyp köçe, jaý 8', ['+99364555666']),
                ('legal', 'Galkynyş köçe, bina 3', ['+99312456789']),
                ('individual', 'Oguzhan köçe, jaý 77', ['+99363222333']),
                ('legal', 'Täzelikleriň köçe, bina 11', ['+99312111222', '+99312333444']),
                ('individual', 'Garaşsyzlyk şaýoly, jaý 25', ['+99365444555']),
                ('legal', 'Ruhnama köçe, bina 5', ['+99322123456']),
            ]
            
            admin_user = User.query.filter_by(username='admin').first()
            
            for client_type, address, phones in subscribers_data:
                sub = Subscriber(client_type=client_type, address=address, debt=0)
                db.session.add(sub)
                db.session.flush()
                
                for phone in phones:
                    p = Phone(subscriber_id=sub.id, number=phone)
                    db.session.add(p)
            
            db.session.commit()
            print(f"Created {len(subscribers_data)} subscribers")
            
            # Create mock orders (sub_id, new_bottles, exchange, water, free, paid_percent)
            # paid_percent: 1.0 = full payment, 0.5 = half paid (credit), 0 = no payment (full credit)
            prices = {p.operation_type: p for p in Price.query.all()}
            subscribers = Subscriber.query.all()
            
            orders_data = [
                (1, 5, 0, 0, 0, 1.0),    # 5 new bottles, full payment
                (2, 0, 3, 2, 0, 0.5),    # 3 exchange + 2 water, 50% paid (credit)
                (3, 2, 1, 0, 1, 1.0),    # 2 new + 1 exchange + 1 free, full payment
                (4, 10, 5, 5, 0, 0.7),   # big order, 70% paid (credit)
                (5, 0, 0, 5, 0, 0.0),    # water only, no payment (full credit)
                (1, 3, 2, 1, 2, 0.8),    # another order, 80% paid (credit)
                (6, 0, 10, 0, 0, 1.0),   # 10 exchanges, full payment
                (7, 1, 0, 1, 0, 0.5),    # 1 new + 1 water, 50% paid (credit)
            ]
            
            for sub_id, new, exchange, water, free, paid_percent in orders_data:
                sub = Subscriber.query.get(sub_id)
                
                # Manual calc for seed to match new logic
                if sub.client_type == 'legal':
                    total = (new * prices['new_bottle'].legal_price + 
                            exchange * prices['exchange'].legal_price + 
                            water * prices['water_only'].legal_price +
                            free * prices['container'].legal_price)
                else:
                    total = (new * prices['new_bottle'].individual_price + 
                            exchange * prices['exchange'].individual_price + 
                            water * prices['water_only'].individual_price +
                            free * prices['container'].individual_price)
                
                paid = Decimal(str(float(total) * paid_percent))
                
                order = Order(
                    subscriber_id=sub_id,
                    user_id=admin_user.id,
                    new_bottles=new,
                    exchange_bottles=exchange,
                    water_only=water,
                    free_bottles=free,
                    total_amount=Decimal(str(total)),
                    paid_amount=paid,
                    created_at=datetime.now() - timedelta(days=sub_id)
                )
                db.session.add(order)
                sub.debt += Decimal(str(total))
            
            db.session.commit()
            print(f"Created {len(orders_data)} orders")
            
            # Add some payments
            payments_data = [(1, 200), (2, 100), (4, 500)]
            for sub_id, amount in payments_data:
                payment = Payment(
                    subscriber_id=sub_id,
                    user_id=admin_user.id,
                    amount=Decimal(str(amount))
                )
                db.session.add(payment)
                sub = Subscriber.query.get(sub_id)
                sub.debt -= Decimal(str(amount))
            
            db.session.commit()
            print("Payments added")
        
        print("\n✅ Database seeded successfully!")

if __name__ == '__main__':
    seed()
