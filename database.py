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


# 기본 문의 카테고리 (slug, 이름, 설명)
DEFAULT_CATEGORIES = [
    ("order", "주문 · 배송", "주문 확인, 배송 조회, 배송지 변경"),
    ("payment", "결제 · 환불", "결제 오류, 환불 요청, 영수증 발급"),
    ("account", "회원 · 계정", "로그인 문제, 비밀번호 변경, 회원 탈퇴"),
    ("product", "상품 문의", "재고, 사이즈, 상품 상세 정보"),
    ("tech", "기술 지원", "사이트 오류, 앱 사용법, 버그 신고"),
    ("etc", "기타 문의", "제휴, 제안, 그 밖의 모든 문의"),
]


def init_db():
    """테이블을 만들고, 기본 카테고리와 테스트용 상담원 계정을 넣어 둡니다."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        # INSERT OR IGNORE: 이미 있으면(slug 중복) 무시하고 넘어감
        conn.executemany(
            "INSERT OR IGNORE INTO categories (slug, name, description, sort_order) "
            "VALUES (?, ?, ?, ?)",
            [(s, n, d, i) for i, (s, n, d) in enumerate(DEFAULT_CATEGORIES)],
        )

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
