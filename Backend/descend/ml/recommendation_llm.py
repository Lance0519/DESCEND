"""Optional LLM-enhanced recommendations.

Supports:
- **Google Gemini** — REST ``generateContent`` (set ``GEMINI_API_KEY`` or ``T2DM_GEMINI_API_KEY``).
- **OpenAI-compatible** Chat Completions — e.g. OpenAI, Azure, local proxies
  (set ``T2DM_LLM_API_KEY`` or ``OPENAI_API_KEY``).

Uses only the standard library for HTTP. On failure, callers keep rule-based recommendations.

Privacy: prompts send aggregated metrics and key-factor strings — not names of relatives.
Review data handling for your IRB / deployment policy.
"""

from __future__ import annotations

import json
import os
import re
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def _log_warning(msg: str) -> None:
    try:
        from flask import current_app

        current_app.logger.warning(msg)
    except RuntimeError:
        pass


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _extract_json_value(text: str) -> Any | None:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _normalize_recommendations(raw: Any) -> list[dict[str, str]] | None:
    if not isinstance(raw, list):
        return None
    out: list[dict[str, str]] = []
    for item in raw[:4]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()[:220]
        desc = str(item.get("description", "")).strip()[:900]
        pr = str(item.get("priority", "medium")).strip().lower()
        if pr not in {"high", "medium", "low"}:
            pr = "medium"
        if title and desc:
            out.append({"title": title, "description": desc, "priority": pr})
    return out or None


def _post_chat_completions(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float,
) -> dict[str, Any] | None:
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "temperature": 0.35,
        "max_tokens": 1400,
        "messages": messages,
    }
    payload = json.dumps(body).encode("utf-8")
    req = Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        _log_warning(f"recommendation_llm (openai): request failed: {exc}")
        return None


def _post_gemini_generate(
    *,
    api_key: str,
    model: str,
    system_text: str,
    user_text: str,
    timeout: float,
) -> dict[str, Any] | None:
    """Call Gemini ``generateContent`` (v1beta)."""
    base = (
        os.getenv("T2DM_GEMINI_API_BASE")
        or "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    # Model id in path, API key as query param (Google AI Studio / API key auth)
    m = model.strip()
    if not m.startswith("models/"):
        m = f"models/{m}"
    url = f"{base}/{m}:generateContent?key={quote(api_key, safe='')}"
    body = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 1400,
            "responseMimeType": "application/json",
        },
    }
    payload = json.dumps(body).encode("utf-8")
    req = Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:900]
        except OSError:
            pass
        _log_warning(
            f"recommendation_llm (gemini): HTTP {exc.code} {exc.reason!r} model={model!r} body={detail!s}"
        )
        return None
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        _log_warning(f"recommendation_llm (gemini): request failed: {exc}")
        return None


def _text_from_gemini_response(data: dict[str, Any]) -> str | None:
    try:
        c0 = data["candidates"][0]
        reason = c0.get("finishReason")
        if reason and reason not in ("STOP", "MAX_TOKENS"):
            _log_warning(f"recommendation_llm (gemini): finishReason={reason}")
        parts = c0["content"]["parts"]
        return "".join(str(p.get("text", "")) for p in parts)
    except (KeyError, IndexError, TypeError):
        return None


def _resolve_llm_route() -> tuple[str, str] | None:
    """Return (\"gemini\", api_key) or (\"openai\", api_key), or None."""
    gemini_key = (
        os.getenv("T2DM_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    ).strip()
    openai_key = (
        os.getenv("T2DM_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    ).strip()
    forced = (os.getenv("T2DM_LLM_PROVIDER") or "").strip().lower()

    if forced == "openai" and openai_key:
        return "openai", openai_key
    if forced == "gemini" and gemini_key:
        return "gemini", gemini_key
    if forced in {"openai", "gemini"}:
        return None

    if gemini_key:
        return "gemini", gemini_key
    if openai_key:
        return "openai", openai_key
    return None


def maybe_llm_recommendations(
    baseline: list[dict[str, Any]],
    *,
    derived_metrics: dict[str, Any],
    key_factors: list[str],
    summary: dict[str, Any],
    personal: dict[str, Any],
    family_history: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (recommendations, provenance).

    provenance includes ``source`` of ``rules`` or ``llm``, optional ``provider``,
    ``model``, and ``error``.
    """
    provenance: dict[str, Any] = {"source": "rules"}
    if not _env_bool("T2DM_LLM_RECOMMENDATIONS_ENABLED", True):
        return baseline, provenance

    route = _resolve_llm_route()
    if not route:
        return baseline, provenance

    provider, api_key = route
    try:
        timeout = float(os.getenv("T2DM_LLM_TIMEOUT", "25"))
    except ValueError:
        timeout = 25.0

    context = {
        "respondentProfile": {
            "age": personal.get("age"),
            "sex": personal.get("sex"),
            "isFilipino": personal.get("isFilipino"),
            "bmi": derived_metrics.get("bmi"),
            "selfReportedT2dm": personal.get("diagnosedT2dm"),
            "selfReportedHypertension": personal.get("diagnosedHypertension"),
        },
        "lifestyleSurvey": {
            "physicalActivityScore": family_history.get("physicalActivityScore"),
            "dietQualityScore": family_history.get("dietQualityScore"),
        },
        "riskSummary": {
            "overallRiskBand": summary.get("overallRiskBand"),
            "averagePercentage": summary.get("averagePercentage"),
            "lineageRiskIndex": derived_metrics.get("lineageRiskIndex"),
            "weightedFamilyScore": derived_metrics.get("weightedFamilyScore"),
            "firstDegreeT2dmYes": derived_metrics.get("firstDegreeYesCount"),
            "secondDegreeT2dmYes": derived_metrics.get("secondDegreeYesCount"),
            "diabeticRelativesCount": derived_metrics.get("diabeticRelativesCount"),
        },
        "keyFactors": key_factors[:12],
        "ruleBasedRecommendationSeeds": [
            {"title": r.get("title"), "priority": r.get("priority")} for r in baseline[:6]
        ],
    }

    system = (
        "You are a clinical health education assistant for Type 2 diabetes mellitus (T2DM) "
        "risk awareness among Filipino adults. You provide prevention-oriented, non-diagnostic "
        "suggestions aligned with public-health guidance (nutrition, activity, screening, "
        "blood pressure, weight, follow-up with licensed clinicians). "
        "Do not diagnose or prescribe medication. Use clear, respectful English. "
        "Output a single JSON object only, no markdown, with this shape:\n"
        '{"recommendations":[{"title":"string","description":"string","priority":"high|medium|low"}]}\n'
        "Provide 3 or 4 items. Priorities should match clinical urgency. "
        "Incorporate the seed themes from ruleBasedRecommendationSeeds when relevant, "
        "but improve wording and add specific, actionable detail."
    )
    user_msg = (
        "Using this structured assessment context, produce recommendations JSON.\n\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )

    raw_resp: dict[str, Any] | None = None
    model_label = ""

    if provider == "gemini":
        model_label = (
            os.getenv("T2DM_GEMINI_MODEL") or "gemini-2.0-flash"
        ).strip()
        raw_resp = _post_gemini_generate(
            api_key=api_key,
            model=model_label,
            system_text=system,
            user_text=user_msg,
            timeout=timeout,
        )
        content = _text_from_gemini_response(raw_resp) if raw_resp else None
    else:
        base_url = (
            os.getenv("T2DM_LLM_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        model_label = (os.getenv("T2DM_LLM_MODEL") or "gpt-4o-mini").strip()
        raw_resp = _post_chat_completions(
            base_url=base_url,
            api_key=api_key,
            model=model_label,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            timeout=timeout,
        )
        content = None
        if raw_resp:
            try:
                content = raw_resp["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                content = None

    if not content:
        provenance["error"] = "llm_request_failed"
        provenance["provider"] = provider
        provenance["model"] = model_label or None
        return baseline, provenance

    parsed = _extract_json_value(str(content))
    if not isinstance(parsed, dict):
        provenance["error"] = "llm_json_parse"
        provenance["provider"] = provider
        return baseline, provenance

    recs_raw = parsed.get("recommendations")
    normalized = _normalize_recommendations(recs_raw)
    if not normalized:
        provenance["error"] = "llm_empty_recommendations"
        provenance["provider"] = provider
        return baseline, provenance

    provenance["source"] = "llm"
    provenance["provider"] = provider
    provenance["model"] = model_label
    return normalized, provenance
