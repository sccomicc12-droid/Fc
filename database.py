"""
데이터베이스(SQLite) 연결과 초기화를 담당하는 파일
SQLite는 파일 하나(app.db)에 모든 데이터를 저장하는 가벼운 DB입니다.
"""
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "app.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_connection():
    """DB 연결을 하나 만들어 돌려줍니다."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 결과를 row["username"]처럼 이름으로 꺼낼 수 있게 함
    return conn


def init_db():
    """테이블을 만들고, 테스트용 상담원 계정이 없으면 하나 만들어 둡니다."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", ("agent",)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO users (username, password_hash, nickname, role) "
                "VALUES (?, ?, ?, 'agent')",
                ("agent", generate_password_hash("agent1234"), "상담원"),
            )
            print("[DB] 테스트 상담원 계정 생성: agent / agent1234")
