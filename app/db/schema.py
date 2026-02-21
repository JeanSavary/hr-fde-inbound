from app.db.connection import get_db


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cities (
                name        TEXT PRIMARY KEY,
                state       TEXT NOT NULL,
                region      TEXT NOT NULL,
                lat         REAL NOT NULL,
                lng         REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS loads (
                load_id TEXT PRIMARY KEY,
                origin TEXT NOT NULL,
                origin_lat REAL NOT NULL,
                origin_lng REAL NOT NULL,
                destination TEXT NOT NULL,
                dest_lat REAL NOT NULL,
                dest_lng REAL NOT NULL,
                pickup_datetime TEXT NOT NULL,
                delivery_datetime TEXT NOT NULL,
                equipment_type TEXT NOT NULL,
                loadboard_rate REAL NOT NULL,
                notes TEXT DEFAULT '',
                weight INTEGER NOT NULL,
                commodity_type TEXT NOT NULL,
                num_of_pieces INTEGER DEFAULT 0,
                miles INTEGER NOT NULL,
                dimensions TEXT DEFAULT '',
                status TEXT DEFAULT 'available'
            );

            CREATE TABLE IF NOT EXISTS offers (
                offer_id TEXT PRIMARY KEY,
                call_id TEXT,
                load_id TEXT NOT NULL,
                mc_number TEXT NOT NULL,
                offer_amount REAL NOT NULL,
                offer_type TEXT NOT NULL,
                round_number INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS calls (
                id TEXT PRIMARY KEY,
                call_id TEXT NOT NULL,
                mc_number TEXT,
                carrier_name TEXT,
                lane_origin TEXT,
                lane_destination TEXT,
                equipment_type TEXT,
                load_id TEXT,
                initial_rate REAL,
                final_rate REAL,
                negotiation_rounds INTEGER DEFAULT 0,
                carrier_phone TEXT,
                special_requests TEXT,
                outcome TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                duration_seconds INTEGER,
                transcript TEXT,
                created_at TEXT NOT NULL
            );
        """)
