"""
Create or update an admin user (local / dev).

Loads environment from backend/.env.mysql and backend/.env (same as Flask).

Do not commit real passwords. Example:

  cd backend
  .\\venv\\Scripts\\Activate.ps1
  python scripts/create_admin_user.py --name "Your Name" --email "you@example.com" --password "YourSecurePassword"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent
_backend_root = str(_backend_dir)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

load_dotenv(_backend_dir / ".env.mysql", override=False)
load_dotenv(_backend_dir / ".env", override=False)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402
from app.api.auth import _normalize_email, _validate_password  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or promote an admin user.")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Password (meets same rules as registration)")
    args = parser.parse_args()

    email = _normalize_email(args.email)
    name = str(args.name).strip()
    password = str(args.password)

    if len(name) < 2:
        print("Name must be at least 2 characters long.", file=sys.stderr)
        return 1

    issues = _validate_password(password, email, name)
    if issues:
        for line in issues:
            print(line, file=sys.stderr)
        return 1

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.name = name
            user.role = "admin"
            user.is_active = True
            user.set_password(password)
            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()
            print(f"Updated existing account {email!r}: role=admin, password reset, lock cleared.")
        else:
            user = User(name=name, email=email, role="admin")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"Created admin account {email!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
