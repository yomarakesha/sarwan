import json
from datetime import datetime
from flask_login import current_user
from app import db
from app.models import ActionLog

def log_action(action, entity=None, entity_id=None, details=None):
    """Log user action to database"""
    if current_user.is_authenticated:
        log = ActionLog(
            user_id=current_user.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=json.dumps(details, ensure_ascii=False) if details else None
        )
        db.session.add(log)
        db.session.commit()
