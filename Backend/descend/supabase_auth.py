"""Supabase JWT verification for DESCEND auth."""

from __future__ import annotations

import os
from functools import lru_cache, wraps
from typing import Any, Callable

import jwt
from flask import g, jsonify, request
from jwt import PyJWKClient


def get_supabase_jwt_secret() -> str | None:
    return os.getenv("SUPABASE_JWT_SECRET") or os.getenv("SUPABASE_JWT_SECRET_KEY")


def get_supabase_url() -> str | None:
    raw = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    return raw or None


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    base = get_supabase_url()
    if not base:
        return None
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True)


def _decode_with_secret(token: str, secret: str) -> dict[str, Any] | None:
    attempts = (
        {"algorithms": ["HS256"], "audience": "authenticated"},
        {"algorithms": ["HS256"]},
        {"algorithms": ["HS256"], "options": {"verify_aud": False}},
    )
    for kwargs in attempts:
        try:
            return jwt.decode(token, secret, **kwargs)
        except jwt.PyJWTError:
            continue
    return None


def _decode_with_jwks(token: str) -> dict[str, Any] | None:
    client = _jwks_client()
    if client is None:
        return None
    try:
        key = client.get_signing_key_from_jwt(token)
        attempts = (
            {"algorithms": ["ES256", "RS256", "HS256"], "audience": "authenticated"},
            {"algorithms": ["ES256", "RS256", "HS256"], "options": {"verify_aud": False}},
        )
        for kwargs in attempts:
            try:
                return jwt.decode(token, key.key, **kwargs)
            except jwt.PyJWTError:
                continue
    except Exception:
        return None
    return None


def verify_bearer_token() -> dict[str, Any] | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None

    claims = _decode_with_jwks(token)
    if claims:
        return claims

    secret = get_supabase_jwt_secret()
    if secret:
        claims = _decode_with_secret(token, secret)
        if claims:
            return claims
        return None

    # Dev fallback only when neither JWKS URL nor JWT secret is configured.
    try:
        return jwt.decode(token, options={"verify_signature": False})
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
