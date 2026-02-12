from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text


def split_sql_statements(sql: str) -> list[str]:
    statements = []
    current: list[str] = []
    in_dollar = False
    for line in sql.splitlines(keepends=True):
        stripped = line.strip()
        if "$$" in line:
            in_dollar = not in_dollar
        current.append(line)
        if not in_dollar and stripped.endswith(";"):
            statements.append("".join(current).strip())
            current = []
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return [s for s in statements if s and not s.startswith("--")]


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    migrations_dir = root / "db" / "migrations"
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/my_finance")
    engine = create_engine(database_url, future=True, pool_pre_ping=True)

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        print("No migration files found.")
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                create table if not exists schema_migrations (
                  filename text primary key,
                  applied_at timestamptz not null default now()
                )
                """
            )
        )
        applied = {
            row[0]
            for row in conn.execute(text("select filename from schema_migrations")).fetchall()
        }

        for file in migration_files:
            if file.name in applied:
                continue
            sql = file.read_text(encoding="utf-8")
            for stmt in split_sql_statements(sql):
                conn.execute(text(stmt))
            conn.execute(
                text("insert into schema_migrations (filename) values (:filename)"),
                {"filename": file.name},
            )
            print(f"Applied: {file.name}")

    print("Migration run finished.")


if __name__ == "__main__":
    main()
