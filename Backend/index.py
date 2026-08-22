"""Vercel / WSGI entry for DESCEND Flask API."""

from descend import create_app

app = create_app()
