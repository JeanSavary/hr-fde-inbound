from app.db.connection import get_db


def get_all_settings() -> dict[str, float | str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value, text_value FROM negotiation_settings"
        ).fetchall()
    result: dict[str, float | str] = {}
    for r in rows:
        if r["text_value"] is not None:
            result[r["key"]] = r["text_value"]
        else:
            result[r["key"]] = r["value"]
    return result


def get_setting(key: str) -> float | str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value, text_value FROM negotiation_settings WHERE key=?",
            (key,),
        ).fetchone()
    if row is None:
        return None
    if row["text_value"] is not None:
        return row["text_value"]
    return row["value"]


def upsert_setting(key: str, value: float) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO negotiation_settings (key, value)
               VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value),
        )


def upsert_all(settings: dict[str, float | str | int]) -> dict[str, float | str]:
    with get_db() as conn:
        for key, value in settings.items():
            if isinstance(value, str):
                conn.execute(
                    """INSERT INTO negotiation_settings (key, value, text_value)
                       VALUES (?, NULL, ?)
                       ON CONFLICT(key) DO UPDATE
                       SET text_value=excluded.text_value, value=NULL""",
                    (key, value),
                )
            else:
                conn.execute(
                    """INSERT INTO negotiation_settings (key, value, text_value)
                       VALUES (?, ?, NULL)
                       ON CONFLICT(key) DO UPDATE
                       SET value=excluded.value, text_value=NULL""",
                    (key, value),
                )
    return get_all_settings()
