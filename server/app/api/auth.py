from flask import Blueprint, current_app, jsonify, request, session
from functools import wraps
import json
import ipaddress
import os
from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer


auth = Blueprint("auth", __name__, url_prefix="/auth")

SESSION_USER_KEY = "manifest_user"
DEV_TOKEN_HEADER = "X-Manifest-Dev-Token"
DEV_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _parse_local_dev_user():
    allow_dev_auth = str(
        current_app.config.get("MANIFEST_ALLOW_LOCAL_DEV_AUTH", os.environ.get("FLASK_ENV", ""))
    ).lower()
    if allow_dev_auth not in {"1", "true", "on", "development", "dev"} and not current_app.debug and not current_app.testing:
        return None

    host = request.host.split(":", 1)[0].lower()
    remote = (request.remote_addr or "").lower()
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip().lower()

    def is_local_addr(addr):
        if not addr:
            return False
        if addr in DEV_HOSTS:
            return True
        try:
            parsed = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            return False
        return parsed.is_loopback

    if not (
        host in DEV_HOSTS
        or is_local_addr(remote)
        or is_local_addr(forwarded)
    ):
        return None

    forwarded = forwarded.replace("::ffff:", "")
    remote = remote.replace("::ffff:", "")

    host = host.replace("::ffff:", "")
    token = request.headers.get(DEV_TOKEN_HEADER)
    if not token:
        return None
    if host not in DEV_HOSTS:
        return None

    token = request.headers.get(DEV_TOKEN_HEADER)
    if not token:
        return None

    token = token.strip()
    if not token:
        return None

    try:
        payload = json.loads(token)
        if isinstance(payload, dict) and payload.get("role"):
            return payload
    except Exception:
        pass

    normalized = token.lower()
    if normalized not in {"admin", "manager", "viewer"}:
        return None

    return {
        "id": "dev-user",
        "email": "dev@local.test",
        "first_name": "Dev",
        "last_name": "User",
        "role": normalized,
    }


def _serializer():
    secret = current_app.config.get("MANIFEST_ACCESS_SECRET")
    if not secret:
        raise RuntimeError("MANIFEST_ACCESS_SECRET is not configured")
    return URLSafeTimedSerializer(secret_key=secret, salt="manifest-destiny-access")


def get_manifest_user():
    dev_user = _parse_local_dev_user()
    if dev_user:
        return dev_user
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
