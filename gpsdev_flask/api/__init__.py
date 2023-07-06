from functools import wraps
from flask_login import current_user
from flask import jsonify, current_app


def api_login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'status': '403',
                'title': 'unauthorized',
                'description': 'please log in to access api'
            }), 403
        if callable(getattr(current_app, "ensure_sync", None)):
            return current_app.ensure_sync(func)(*args, **kwargs)
        return func(*args, **kwargs)
    return decorated_view
