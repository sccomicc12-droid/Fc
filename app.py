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

import chat
import points
from config import CONSULT_TYPES, GRADES, SCHOOL_INFO
from database import BASE_DIR, get_connection, init_db
from helpers import ApiError, current_user, login_required, public_user, socketio

# static/ : CSS, JS 같은 누구나 받아도 되는 파일
# pages/  : HTML 페이지. 서버가 로그인 여부를 확인한 뒤에만 보내줍니다.
app = Flask(__name__, static_folder="static", static_url_path="")
PAGES_DIR = BASE_DIR / "pages"
# 세션(로그인 상태)을 암호화하는 비밀 키. 실제 서비스에서는 환경변수로 관리해야 합니다.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# 기능별로 나눈 API 묶음(Blueprint)을 등록
app.register_blueprint(chat.bp)     # /api/chat/...   1:1 상담
app.register_blueprint(points.bp)   # /api/points...  포인트 충전/결제
socketio.init_app(app)              # 실시간 통신(웹소켓) 연결

USERNAME_RULE = re.compile(r"^[a-zA-Z0-9_]{4,20}$")
PHONE_RULE = re.compile(r"^01[016789]\d{7,8}$")  # 하이픈을 뺀 휴대폰 번호


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify(error=err.message), err.status


def validate_account(username, password):
    """아이디/비밀번호 규칙 검사 (회원가입, 학교 신청에서 같이 사용)"""
    if not USERNAME_RULE.match(username):
        raise ApiError("아이디는 영문/숫자/_ 4~20자여야 합니다.")
    if len(password) < 8:
        raise ApiError("비밀번호는 8자 이상이어야 합니다.")


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


@app.get("/start")
def start_page():
    return page("start.html")


@app.get("/customer")
def customer_page():
    # 백엔드에서 접근 권한 검사: 로그인 안 했으면 로그인 페이지로 보냄
    user = current_user()
    if user is None:
        return redirect("/login?next=/customer")
    if user["role"] == "agent":
        return redirect("/agent")
    return page("customer.html")


@app.get("/wallet")
def wallet_page():
    user = current_user()
    if user is None:
        return redirect("/login?next=/wallet")
    if user["role"] == "agent":
        return redirect("/agent")
    return page("wallet.html")


@app.get("/agent")
def agent_page():
    user = current_user()
    if user is None:
        return redirect("/login?next=/agent")
    if user["role"] != "agent":
        return redirect("/customer")  # 고객은 상담원 화면에 들어올 수 없음
    return page("agent.html")


@app.get("/form-demo")
def form_demo_page():
    # 누구나 볼 수 있는 입력 폼 UI 패턴 예제 (로그인 불필요)
    return page("form-demo.html")


# ---------------------------------------------------------------------------
# 입력 폼 예제 API
# ---------------------------------------------------------------------------
@app.post("/api/demo/echo")
def demo_echo():
    """폼에서 받은 값을 서버가 검사한 뒤 그대로 돌려줍니다.
    '프론트에서 보낸 값을 백엔드가 어떻게 받는지' 보여주는 교육용 예제입니다.
    실제로 저장하지 않으므로 민감한 정보는 넣지 마세요."""
    d = request.get_json(silent=True) or {}

    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip()
    topic = d.get("topic")
    visit_date = (d.get("visit_date") or "").strip()
    headcount = d.get("headcount")
    channels = d.get("channels")
    message = (d.get("message") or "").strip()
    agree = d.get("agree")

    # --- 서버 측 검사 (프론트 검사는 우회할 수 있으므로 서버에서 다시 확인) ---
    errors = {}
    if not 2 <= len(name) <= 20:
        errors["name"] = "이름을 2~20자로 입력해 주세요."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors["email"] = "이메일 형식이 올바르지 않습니다."
    if topic not in ("product", "price", "support", "etc"):
        errors["topic"] = "문의 유형을 선택해 주세요."
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", visit_date or ""):
        errors["visit_date"] = "날짜를 선택해 주세요."
    try:
        headcount = int(headcount)
        if not 1 <= headcount <= 100:
            raise ValueError
    except (TypeError, ValueError):
        errors["headcount"] = "인원을 1~100명으로 입력해 주세요."
    if not isinstance(channels, list) or not channels:
        errors["channels"] = "연락 받을 방법을 하나 이상 선택해 주세요."
    if len(message) > 300:
        errors["message"] = "메시지는 300자까지 입력할 수 있습니다."
    if agree is not True:
        errors["agree"] = "약관에 동의해야 제출할 수 있습니다."

    if errors:
        return jsonify(error="입력값을 확인해 주세요.", fields=errors), 400

    # 검사를 통과한 '정리된 값'을 돌려줍니다.
    return jsonify(received={
        "name": name,
        "email": email,
        "topic": topic,
        "visit_date": visit_date,
        "headcount": headcount,
        "channels": channels,
        "message": message,
        "agree": agree,
    })


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
# 학교 상담 신청 API
# ---------------------------------------------------------------------------
@app.get("/api/school/info")
def school_info():
    """신청 화면에 필요한 정보 (학년, 상담 유형, 요금, 연락처)"""
    return jsonify(grades=GRADES, consult_types=CONSULT_TYPES, **SCHOOL_INFO)


@app.get("/api/school/my")
@login_required()
def my_application(user):
    """내 가장 최근 학교 상담 신청서 (없으면 null)"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT grade, consult_type, anonymous, created_at FROM applications "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
    if row is None:
        return jsonify(application=None)
    names = {t["slug"]: t["name"] for t in CONSULT_TYPES}
    return jsonify(application={**dict(row), "consult_name": names.get(row["consult_type"], "")})


@app.post("/api/school/apply")
def school_apply():
    d = request.get_json(silent=True) or {}
    grade = d.get("grade")
    real_name = (d.get("real_name") or "").strip()
    phone = re.sub(r"\D", "", d.get("phone") or "")  # 숫자만 남김
    username = (d.get("username") or "").strip()
    password = d.get("password") or ""
    code = (d.get("school_code") or "").strip().upper()
    consult_type = d.get("consult_type")
    anonymous = d.get("anonymous")
    privacy = d.get("privacy_agree")
    satisfaction = d.get("satisfaction")

    # --- 1) 입력값 검사 ---
    try:
        grade = int(grade)
    except (TypeError, ValueError):
        grade = None
    if grade not in GRADES:
        raise ApiError("학년을 선택해 주세요.")
    if not 2 <= len(real_name) <= 20:
        raise ApiError("이름을 2~20자로 입력해 주세요.")
    if not PHONE_RULE.match(phone):
        raise ApiError("전화번호 형식이 올바르지 않습니다. (예: 010-1234-5678)")
    validate_account(username, password)
    if not code:
        raise ApiError("학교에서 받은 코드를 입력해 주세요.")
    if consult_type not in {t["slug"] for t in CONSULT_TYPES}:
        raise ApiError("상담 유형을 선택해 주세요.")
    if anonymous not in ("yes", "no"):
        raise ApiError("익명 여부를 선택해 주세요.")
    # 개인정보는 동의 없이 수집할 수 없으므로 '아니요'면 신청 불가
    if privacy != "yes":
        raise ApiError("개인정보 수집·이용에 동의해야 신청할 수 있습니다.")
    if satisfaction not in (None, ""):
        try:
            satisfaction = int(satisfaction)
        except (TypeError, ValueError):
            satisfaction = 0
        if not 1 <= satisfaction <= 5:
            raise ApiError("만족도는 1~5점 중에서 선택해 주세요.")
    else:
        satisfaction = None
    phone = f"{phone[:3]}-{phone[3:-4]}-{phone[-4:]}"

    # --- 2) DB 저장 ---
    # with 블록 안에서 오류(raise)가 나면 지금까지의 저장이 모두 취소(rollback)됩니다.
    # 그래서 "회원은 만들어졌는데 코드는 그대로" 같은 어중간한 상태가 생기지 않습니다.
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT used_by FROM school_codes WHERE code = ?", (code,)
            ).fetchone()
            if row is None:
                raise ApiError("유효하지 않은 학교 코드입니다.")
            if row["used_by"] is not None:
                raise ApiError("이미 사용된 학교 코드입니다.", 409)

            cur = conn.execute(
                "INSERT INTO users (username, password_hash, nickname, real_name, phone, grade) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, generate_password_hash(password), real_name, real_name, phone, grade),
            )
            user_id = cur.lastrowid

            # used_by IS NULL 조건: 두 명이 동시에 같은 코드를 써도 한 명만 성공
            used = conn.execute(
                "UPDATE school_codes SET used_by = ?, used_at = datetime('now', 'localtime') "
                "WHERE code = ? AND used_by IS NULL",
                (user_id, code),
            )
            if used.rowcount != 1:
                raise ApiError("이미 사용된 학교 코드입니다.", 409)

            conn.execute(
                "INSERT INTO applications (user_id, grade, consult_type, anonymous, privacy_agree, satisfaction) "
                "VALUES (?, ?, ?, ?, 1, ?)",
                (user_id, grade, consult_type, 1 if anonymous == "yes" else 0, satisfaction),
            )
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise ApiError("이미 사용 중인 아이디입니다.", 409)

    # 신청과 동시에 로그인 처리
    session.clear()
    session["user_id"] = user_id
    return jsonify(message="상담 신청이 완료되었습니다.", user=public_user(user)), 201


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
    validate_account(username, password)
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


if __name__ == "__main__":
    init_db()
    # HOST=0.0.0.0 으로 실행하면 같은 와이파이의 다른 기기(아이패드 등)에서도 접속 가능
    # 웹소켓을 쓰기 때문에 app.run 대신 socketio.run 으로 실행합니다.
    socketio.run(app, debug=True, host=os.environ.get("HOST", "127.0.0.1"), port=5000,
                 allow_unsafe_werkzeug=True)
