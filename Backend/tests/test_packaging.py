"""Vercel installs from pyproject.toml [project]; keep it aligned with requirements.txt."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

import jwt

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DESCEND_ROOT = BACKEND_ROOT / "descend"

# Import name → dist pin prefix in [project].dependencies
RUNTIME_IMPORT_TO_DIST = {
    "flask": "Flask==",
    "flask_cors": "Flask-Cors==",
    "flask_sqlalchemy": "Flask-SQLAlchemy==",
    "sqlalchemy": "SQLAlchemy==",
    "werkzeug": "Werkzeug==",
    "itsdangerous": "itsdangerous==",
    "networkx": "networkx==",
    "pymysql": "pymysql==",
    "psycopg2": "psycopg2-binary==",
    "dotenv": "python-dotenv==",
    "sklearn": "scikit-learn==",
    "joblib": "joblib==",
    "jwt": "PyJWT==",
    "cryptography": "cryptography==",
}

SCRIPTS_IMPORT_TO_DIST = {
    "pandas": "pandas==",
    "openpyxl": "openpyxl==",
}


def _requirement_pins(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _pyproject() -> dict:
    return tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_pyproject_dependencies_match_requirements_txt() -> None:
    requirements = _requirement_pins((BACKEND_ROOT / "requirements.txt").read_text(encoding="utf-8"))
    declared = list(_pyproject()["project"]["dependencies"])
    assert declared == requirements, (
        "Vercel `uv lock` uses [project].dependencies; copy every pin from requirements.txt. "
        f"missing={sorted(set(requirements) - set(declared))} extra={sorted(set(declared) - set(requirements))}"
    )


def test_serving_third_party_imports_are_declared() -> None:
    declared = list(_pyproject()["project"]["dependencies"])
    missing: list[str] = []
    for path in DESCEND_ROOT.rglob("*.py"):
        for name in _top_level_imports(path):
            if name in sys.stdlib_module_names or name == "descend":
                continue
            prefix = RUNTIME_IMPORT_TO_DIST.get(name)
            if prefix is None:
                missing.append(f"{path.relative_to(BACKEND_ROOT)} imports {name} (undeclared)")
                continue
            if not any(pin.startswith(prefix) for pin in declared):
                missing.append(f"{path.relative_to(BACKEND_ROOT)} imports {name} (no {prefix} pin)")
    assert not missing, "\n".join(missing)


def test_script_and_dev_extras_cover_non_serving_imports() -> None:
    extras = _pyproject()["project"]["optional-dependencies"]
    scripts = extras["scripts"]
    dev = extras["dev"]
    assert any(pin.startswith("pandas==") for pin in scripts)
    assert any(pin.startswith("openpyxl==") for pin in scripts)
    assert any(pin.startswith("pytest==") for pin in dev)

    merge = BACKEND_ROOT / "scripts" / "merge_uploaded_to_training.py"
    assert "pandas" in _top_level_imports(merge)
    source = merge.read_text(encoding="utf-8")
    assert "read_excel" in source


def test_pyjwt_can_use_supabase_asymmetric_algs() -> None:
    """Supabase JWT Signing Keys need cryptography; PyJWT-only installs fail here."""
    for name in ("ES256", "RS256", "HS256"):
        alg = jwt.get_algorithm_by_name(name)
        assert alg is not None, name
        assert re.search(r"HMAC|RSA|ECDSA|EC", type(alg).__name__), type(alg).__name__
    import cryptography  # noqa: PLC0415

    assert cryptography.__version__
