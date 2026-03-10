from functools import wraps

from flask import Blueprint, current_app, jsonify, request, session
from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer


auth = Blueprint("auth", __name__, url_prefix="/auth")

SESSION_USER_KEY = "manifest_user"


def _serializer():
    secret = current_app.config.get("MANIFEST_ACCESS_SECRET")
    if not secret:
        raise RuntimeError("MANIFEST_ACCESS_SECRET is not configured")
    return URLSafeTimedSerializer(secret_key=secret, salt="manifest-destiny-access")


def get_manifest_user():
    return session.get(SESSION_USER_KEY)


def manifest_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not get_manifest_user():
            return jsonify(success=False, message="Authentication required"), 401
        return fn(*args, **kwargs)

    return wrapper


def manifest_admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_manifest_user()
        if not user:
            return jsonify(success=False, message="Authentication required"), 401
        if (user.get("role") or "").lower() != "admin":
            return jsonify(success=False, message="Admin access required"), 403
        return fn(*args, **kwargs)

    return wrapper


@auth.post("/session/exchange")
def exchange_session():
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    if not token:
        return jsonify(success=False, message="token is required"), 400

    try:
        data = _serializer().loads(
            token,
            max_age=current_app.config.get("MANIFEST_ACCESS_TOKEN_MAX_AGE", 300),
        )
        user = {
            "id": data.get("id"),
            "email": data.get("email"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "role": (data.get("role") or "").lower(),
        }
        if not user["id"] or not user["role"]:
            raise ValueError("Token payload missing required user fields")

        session[SESSION_USER_KEY] = user
        session.permanent = True
        return jsonify(success=True, user=user), 200
    except SignatureExpired:
        return jsonify(success=False, message="Manifest access token expired"), 401
    except (BadData, ValueError) as exc:
        return jsonify(success=False, message=str(exc) or "Invalid manifest access token"), 401
    except Exception as exc:
        current_app.logger.exception("[MANIFEST SESSION EXCHANGE ERROR]")
        return jsonify(success=False, message=f"Session exchange failed: {exc}"), 500


@auth.get("/session/hydrate")
def hydrate_session():
    user = get_manifest_user()
    if not user:
        return jsonify(success=False, message="Authentication required"), 401
    return jsonify(success=True, user=user), 200
