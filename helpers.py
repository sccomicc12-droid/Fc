"""
여러 파일에서 같이 쓰는 도우미 함수 모음
"""
from functools import wraps

from flask import session
from flask_socketio import SocketIO

from database import get_connection

# 실시간 통신(웹소켓) 객체. app.py에서 init_app(app)으로 연결합니다.
socketio = SocketIO()


class ApiError(Exception):
    """API에서 오류를 돌려줄 때 사용. raise ApiError("메시지", 400)"""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def current_user():
    """세션에 저장된 user_id로 현재 로그인한 사용자를 DB에서 찾음 (없으면 None)"""
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


def login_required(role=None):
    """로그인(과 역할)이 필요한 API에 붙이는 데코레이터.
    통과하면 함수의 첫 번째 인자로 현재 사용자를 넘겨줍니다.

    @app.get("/api/...")
    @login_required("agent")
    def handler(user): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                raise ApiError("로그인이 필요합니다.", 401)
            if role and user["role"] != role:
                raise ApiError("권한이 없습니다.", 403)
            return func(user, *args, **kwargs)
        return wrapper
    return decorator
