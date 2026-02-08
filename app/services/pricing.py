from app.models import Settings, Order
from decimal import Decimal

def get_promo_water_price(subscriber_id):
    """
    Check if promo price applies for "Water Only".
    
    Returns:
        Decimal: The promo price (e.g. 10.00) if applicable.
        None: If promo does not apply (use standard pricing).
    """
    try:
        # Get promo settings
        promo_price_setting = Settings.query.get('promo_water_price')
        promo_limit_setting = Settings.query.get('promo_water_limit')
        promo_active_setting = Settings.query.get('promo_active')
        
        # Check if promo is globally active
        # Default to False if setting is missing, or True? 
        # Plan said: "If value is not true/1/on, return None".
        # Let's default to True for backward compatibility if not set, or False?
        # User said "activation button", implying it might be off by default or they want control.
        # Let's treat missing as False to be safe, or True to not break existing flow?
        # Safe approach: If missing, assume it's ON (since it was working before). 
        # But if they want to "turn it on", maybe default OFF?
        # Let's check the setting. If it has 'true', '1', 'on', it's active.
        
        is_active = True # Default behavior before this feature
        if promo_active_setting:
             is_active = promo_active_setting.value.lower() in ['true', '1', 'on']
        
        if not is_active:
             return None

        # Defaults if settings missing (fallback)
        promo_price = Decimal(promo_price_setting.value) if promo_price_setting else Decimal('10.00')
        limit = int(promo_limit_setting.value) if promo_limit_setting else 10
        
        # Check subscriber specific settings
        from app.models import Subscriber
        subscriber = Subscriber.query.get(subscriber_id)
        
        # Count existing orders for this subscriber
        # If start date set, only count orders after that date
        query = Order.query.filter_by(subscriber_id=subscriber_id)
        
        if subscriber and subscriber.promo_start_date:
            query = query.filter(Order.created_at >= subscriber.promo_start_date)
            
        order_count = query.count()
        
        if order_count < limit:
            return promo_price
            
        return None
        
    except Exception as e:
        # Log error? Return None to be safe and fall back to standard pricing
        print(f"Error calculating promo price: {e}")
        return None
