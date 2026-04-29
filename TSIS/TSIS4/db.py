# db.py — PostgreSQL integration via psycopg2

import psycopg2
from config import DB_CONFIG


def _connect():
    return psycopg2.connect(**DB_CONFIG)


def init_db() -> None:
    """Create tables if they don't exist yet."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id       SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_sessions (
            id            SERIAL PRIMARY KEY,
            player_id     INTEGER REFERENCES players(id),
            score         INTEGER   NOT NULL,
            level_reached INTEGER   NOT NULL,
            played_at     TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


def get_or_create_player(username: str) -> int:
    """Return player id, creating the record if necessary."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO players (username) VALUES (%s) ON CONFLICT (username) DO NOTHING",
        (username,),
    )
    conn.commit()
    cur.execute("SELECT id FROM players WHERE username = %s", (username,))
    player_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    return player_id


def save_session(player_id: int, score: int, level_reached: int) -> None:
    """Persist one completed game session."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO game_sessions (player_id, score, level_reached) VALUES (%s, %s, %s)",
        (player_id, score, level_reached),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_personal_best(player_id: int) -> int:
    """Return the player's highest score ever, or 0 if none."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT MAX(score) FROM game_sessions WHERE player_id = %s", (player_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row and row[0] is not None else 0


def get_leaderboard() -> list:
    """Return top-10 rows: (rank, username, score, level, played_at)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            ROW_NUMBER() OVER (ORDER BY gs.score DESC) AS rank,
            p.username,
            gs.score,
            gs.level_reached,
            gs.played_at
        FROM game_sessions gs
        JOIN players p ON gs.player_id = p.id
        ORDER BY gs.score DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
