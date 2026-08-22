from sqlalchemy import inspect, text

from .extensions import db


def _sql_types_for_dialect(dialect: str) -> dict[str, str]:
    return {
        "datetime": "DATETIME",
        "bool_default_true": "BOOLEAN NOT NULL DEFAULT 1",
        "int": "INTEGER",
    }


def ensure_database_schema() -> None:
    inspector = inspect(db.engine)
    sql_types = _sql_types_for_dialect(db.engine.dialect.name)

    if "assessments" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("assessments")}
        assessment_changes = {
            "user_id": f"ALTER TABLE assessments ADD COLUMN user_id {sql_types['int']}",
            "title": "ALTER TABLE assessments ADD COLUMN title VARCHAR(160) NOT NULL DEFAULT 'Assessment Record'",
        }
        for column, statement in assessment_changes.items():
            if column not in columns:
                db.session.execute(text(statement))

        if "updated_at" not in columns:
            db.session.execute(text(f"ALTER TABLE assessments ADD COLUMN updated_at {sql_types['datetime']}"))
            db.session.execute(text("UPDATE assessments SET updated_at = created_at WHERE updated_at IS NULL"))

    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        user_changes = {
            "is_active": f"ALTER TABLE users ADD COLUMN is_active {sql_types['bool_default_true']}",
            "failed_login_attempts": f"ALTER TABLE users ADD COLUMN failed_login_attempts {sql_types['int']} NOT NULL DEFAULT 0",
            "locked_until": f"ALTER TABLE users ADD COLUMN locked_until {sql_types['datetime']}",
            "reset_token_hash": "ALTER TABLE users ADD COLUMN reset_token_hash VARCHAR(255)",
            "reset_token_expires_at": f"ALTER TABLE users ADD COLUMN reset_token_expires_at {sql_types['datetime']}",
            "last_login_at": f"ALTER TABLE users ADD COLUMN last_login_at {sql_types['datetime']}",
        }
        for column, statement in user_changes.items():
            if column not in columns:
                db.session.execute(text(statement))

    db.session.commit()