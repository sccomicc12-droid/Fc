"""
백엔드 서버 (Flask)
- 정적 파일(HTML/CSS/JS)을 보내주고
- /api/... 주소로 JSON 데이터를 주고받습니다.
"""
import os
import re
import sqlite3

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import BASE_DIR, get_connection, init_db

# static/ : CSS, JS 같은 누구나 받아도 되는 파일
# pages/  : HTML 페이지. 서버가 로그인 여부를 확인한 뒤에만 보내줍니다.
app = Flask(__name__, static_folder="static", static_url_path="")
PAGES_DIR = BASE_DIR / "pages"
# 세션(로그인 상태)을 암호화하는 비밀 키. 실제 서비스에서는 환경변수로 관리해야 합니다.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

USERNAME_RULE = re.compile(r"^[a-zA-Z0-9_]{4,20}$")


# ---------------------------------------------------------------------------
# 페이지
# ---------------------------------------------------------------------------
def page(name):
    return send_from_directory(PAGES_DIR, name)


@app.get("/")
def index():
    return page("index.html")


@app.get("/login")
def login_page():
    return page("login.html")


@app.get("/signup")
def signup_page():
    return page("signup.html")


@app.get("/customer")
def customer_page():
    # 백엔드에서 접근 권한 검사: 로그인 안 했으면 로그인 페이지로 보냄
    user = current_user()
    if user is None:
        return redirect("/login?next=/customer")
    if user["role"] == "agent":
        return redirect("/agent")
    return page("customer.html")


@app.get("/agent")
def agent_page():
    user = current_user()
    if user is None:
        return redirect("/login?next=/agent")
    if user["role"] != "agent":
        return redirect("/customer")  # 고객은 상담원 화면에 들어올 수 없음
    return page("agent.html")


# ---------------------------------------------------------------------------
# 카테고리 API
# ---------------------------------------------------------------------------
@app.get("/api/categories")
def categories():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT slug, name, description FROM categories ORDER BY sort_order"
        ).fetchall()
    return jsonify(categories=[dict(r) for r in rows])


# ---------------------------------------------------------------------------
# 회원 API
# ---------------------------------------------------------------------------
@app.post("/api/signup")
def signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    nickname = (data.get("nickname") or "").strip()

    # 1) 서버에서도 반드시 입력값을 검사합니다. (프론트 검사는 우회할 수 있기 때문)
    if not USERNAME_RULE.match(username):
        return jsonify(error="아이디는 영문/숫자/_ 4~20자여야 합니다."), 400
    if len(password) < 8:
        return jsonify(error="비밀번호는 8자 이상이어야 합니다."), 400
    if not 1 <= len(nickname) <= 20:
        return jsonify(error="닉네임은 1~20자여야 합니다."), 400

    # 2) 비밀번호를 해시로 바꿔 저장합니다.
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, nickname) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), nickname),
            )
    except sqlite3.IntegrityError:  # UNIQUE 제약 위반 = 이미 있는 아이디
        return jsonify(error="이미 사용 중인 아이디입니다."), 409

    return jsonify(message="회원가입이 완료되었습니다."), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    with get_connection() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

    # 아이디가 틀렸는지 비밀번호가 틀렸는지 구분해서 알려주지 않는 것이 보안상 좋습니다.
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify(error="아이디 또는 비밀번호가 올바르지 않습니다."), 401

    session.clear()
    session["user_id"] = user["id"]
    return jsonify(user=public_user(user))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(message="로그아웃되었습니다.")


@app.get("/api/me")
def me():
    """현재 로그인한 사용자 정보. 로그인 안 했으면 user=null"""
    user = current_user()
    return jsonify(user=public_user(user) if user else None)


# ---------------------------------------------------------------------------
# 도우미 함수
# ---------------------------------------------------------------------------
def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def public_user(user):
    """비밀번호 해시 같은 민감 정보는 빼고 프론트에 보낼 정보만 고릅니다."""
    return {
        "id": user["id"],
        "username": user["username"],
        "nickname": user["nickname"],
        "role": user["role"],
    }


if __name__ == "__main__":
    init_db()
    # HOST=0.0.0.0 으로 실행하면 같은 와이파이의 다른 기기(아이패드 등)에서도 접속 가능
    app.run(debug=True, host=os.environ.get("HOST", "127.0.0.1"), port=5000)
