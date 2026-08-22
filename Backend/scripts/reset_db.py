from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text


def reset_database(remove_schema: bool = False) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_dir))

    from descend import create_app
    from descend.extensions import db

    app = create_app()

    with app.app_context():
        dialect = db.engine.dialect.name

        if remove_schema:
            db.drop_all()
            db.create_all()
            print("Dropped and recreated schema.")
            return

        if dialect == "mysql":
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            db.session.execute(text("TRUNCATE TABLE prediction_results"))
            db.session.execute(text("TRUNCATE TABLE assessments"))
            db.session.execute(text("TRUNCATE TABLE users"))
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        else:
            # Safe fallback for sqlite/other dialects.
            db.session.execute(text("DELETE FROM prediction_results"))
            db.session.execute(text("DELETE FROM assessments"))
            db.session.execute(text("DELETE FROM users"))

        db.session.commit()
        print(f"Reset data tables on dialect: {dialect}")


if __name__ == "__main__":
    remove_schema = "--drop-schema" in sys.argv
    try:
        reset_database(remove_schema=remove_schema)
    except Exception as exc:
        print(f"Reset failed: {exc}", file=sys.stderr)
        sys.exit(1)
