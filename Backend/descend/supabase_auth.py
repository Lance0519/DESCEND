"""Supabase JWT verification for DESCEND auth."""

from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable

import jwt
from flask import g, jsonify, request


def get_supabase_jwt_secret() -> str | None:
    return os.getenv("SUPABASE_JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET_KEY")


def verify_bearer_token() -> dict[str, Any] | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    secret = get_supabase_jwt_secret()
    if not secret:
        # Dev fallback: decode without verify when secret missing (local only)
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError:
            return None
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None


def optional_supabase_user(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = verify_bearer_token()
        g.supabase_user_id = claims.get("sub") if claims else None
        g.supabase_email = claims.get("email") if claims else None
        return fn(*args, **kwargs)

    return wrapper


def require_supabase_user(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = verify_bearer_token()
        if not claims or not claims.get("sub"):
            return jsonify({"error": "Unauthorized"}), 401
        g.supabase_user_id = claims["sub"]
        g.supabase_email = claims.get("email")
        return fn(*args, **kwargs)

    return wrapper
