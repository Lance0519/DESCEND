"""Vercel / WSGI entry for DESCEND Flask API.

Vercel looks for a top-level Flask instance named ``app`` in this file
(see https://vercel.com/docs/frameworks/backend/flask).
"""

from app import create_app

app = create_app()
