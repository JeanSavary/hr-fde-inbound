from app.db.connection import get_db


def get_all_settings() -> dict[str, float]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM negotiation_settings"
        ).fetchall()
    return {r["key"]: r["value"] for r in rows}


def get_setting(key: str) -> float | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM negotiation_settings WHERE key=?",
            (key,),
        ).fetchone()
    return row["value"] if row else None


def upsert_setting(key: str, value: float) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO negotiation_settings (key, value)
               VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value),
        )


def upsert_all(settings: dict[str, float]) -> dict[str, float]:
    with get_db() as conn:
        for key, value in settings.items():
            conn.execute(
                """INSERT INTO negotiation_settings (key, value)
                   VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE
                   SET value=excluded.value""",
                (key, value),
            )
    return get_all_settings()
