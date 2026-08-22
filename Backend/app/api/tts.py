"""Text-to-speech endpoint — Google Cloud TTS with graceful fallback."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.request

from flask import Blueprint, Response, jsonify, request

tts_bp = Blueprint("tts", __name__)

_CACHE: dict[str, bytes] = {}


def _synthesize_google(text: str, language: str) -> bytes | None:
    api_key = os.getenv("GOOGLE_TTS_API_KEY")
    if not api_key:
        return None

    voice_name = "fil-PH-Wavenet-A" if language == "tl" else "en-US-Neural2-C"
    language_code = "fil-PH" if language == "tl" else "en-US"
    body = {
        "input": {"text": text[:500]},
        "voice": {"languageCode": language_code, "name": voice_name},
        "audioConfig": {"audioEncoding": "MP3"},
    }
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        audio_b64 = payload.get("audioContent")
        if not audio_b64:
            return None
        return base64.b64decode(audio_b64)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


@tts_bp.post("/tts")
def tts():
    body = request.get_json(silent=True) or {}
    text = str(body.get("text") or "").strip()
    language = str(body.get("language") or "en").lower()
    if language not in {"en", "tl"}:
        language = "en"
    if not text:
        return jsonify({"error": "text required"}), 400

    cache_key = hashlib.sha256(f"{language}:{text}".encode("utf-8")).hexdigest()
    if cache_key in _CACHE:
        return Response(_CACHE[cache_key], mimetype="audio/mpeg")

    audio = _synthesize_google(text, language)
    if audio:
        if len(_CACHE) > 200:
            _CACHE.clear()
        _CACHE[cache_key] = audio
        return Response(audio, mimetype="audio/mpeg")

    # No API key / failure — return empty so client falls back to Web Speech
    return Response(b"", mimetype="audio/mpeg", status=204)
