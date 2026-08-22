"""Minimal Vercel probe — full app restored after health works."""

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "DESCEND API", "mode": "minimal"})
