"""
실시간 1:1 상담 (Socket.IO)

[REST API]  상담방 만들기/목록/수락/종료처럼 '한 번 요청하고 끝나는' 일
[웹소켓]     메시지 주고받기처럼 '서버가 먼저 알려줘야 하는' 실시간 일

웹소켓 채널(room) 이름 규칙
- "agents"      : 모든 상담원. 새 상담 요청, 입금 신청 같은 알림을 받음
- "user:<id>"   : 특정 사용자 한 명. 포인트 적립 알림 등
- "room:<id>"   : 상담방 하나. 그 방의 고객과 상담원이 메시지를 받음
"""
from flask import Blueprint, jsonify, request
from flask_socketio import join_room

from config import CONSULT_TYPES
from database import get_connection
from helpers import ApiError, current_user, login_required, socketio

bp = Blueprint("chat", __name__, url_prefix="/api/chat")

MAX_MESSAGE = 1000

ROOM_SELECT = """
    SELECT r.*, c.nickname AS customer_nickname, a.nickname AS agent_nickname,
           (SELECT body FROM messages m WHERE m.room_id = r.id ORDER BY m.id DESC LIMIT 1) AS last_message
    FROM chat_rooms r
    JOIN users c ON c.id = r.customer_id
    LEFT JOIN users a ON a.id = r.agent_id
"""


# ---------------------------------------------------------------------------
# 도우미
# ---------------------------------------------------------------------------
def room_dict(row):
    return {
        "id": row["id"],
        "status": row["status"],
        "topic": row["topic"],
        "anonymous": bool(row["anonymous"]),
        # 익명 상담이면 상담원에게도 이름을 보여주지 않음
        "customer_name": "익명 학생" if row["anonymous"] else row["customer_nickname"],
        "agent_id": row["agent_id"],
        "agent_name": row["agent_nickname"],
        "last_message": row["last_message"],
        "created_at": row["created_at"],
    }


def message_dict(row):
    return {
        "id": row["id"],
        "room_id": row["room_id"],
        "sender_id": row["sender_id"],
        "kind": row["kind"],
        "body": row["body"],
        "time": row["created_at"][11:16],  # "2026-11-16 14:05:00" → "14:05"
    }


def get_room(conn, room_id):
    row = conn.execute(ROOM_SELECT + " WHERE r.id = ?", (room_id,)).fetchone()
    if row is None:
        raise ApiError("상담방을 찾을 수 없습니다.", 404)
    return row


def can_view(user, room):
    """고객은 자기 방만, 상담원은 모든 방을 볼 수 있음"""
    return user["role"] == "agent" or room["customer_id"] == user["id"]


def add_message(conn, room_id, body, sender_id=None, kind="text"):
    """메시지를 DB에 저장하고 저장된 메시지를 돌려줌.
    실시간 전송(emit_message)은 DB 저장이 끝난(commit) 뒤에 따로 합니다."""
    cur = conn.execute(
        "INSERT INTO messages (room_id, sender_id, kind, body) VALUES (?, ?, ?, ?)",
        (room_id, sender_id, kind, body),
    )
    return message_dict(conn.execute("SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)).fetchone())


def emit_message(msg):
    """그 상담방에 들어와 있는 사람들에게 메시지를 실시간으로 보냄"""
    socketio.emit("message", msg, to=f"room:{msg['room_id']}")


def notify_room_changed(room_id):
    """방 상태가 바뀌면 그 방 사람들과 모든 상담원에게 알림 (commit 이후 호출)"""
    with get_connection() as conn:
        room = room_dict(get_room(conn, room_id))
    socketio.emit("room_update", room, to=f"room:{room_id}")
    socketio.emit("rooms_changed", {"room_id": room_id}, to="agents")


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
@bp.get("/rooms")
@login_required()
def list_rooms(user):
    with get_connection() as conn:
        if user["role"] == "agent":
            # 대기 중인 방 전체 + 내가 맡은 진행 중인 방
            rows = conn.execute(
                ROOM_SELECT + " WHERE r.status = 'waiting' OR (r.status = 'active' AND r.agent_id = ?)"
                " ORDER BY r.status = 'waiting', r.id",
                (user["id"],),
            ).fetchall()
        else:
            rows = conn.execute(
                ROOM_SELECT + " WHERE r.customer_id = ? ORDER BY r.id DESC LIMIT 10", (user["id"],)
            ).fetchall()
    return jsonify(rooms=[room_dict(r) for r in rows])


@bp.post("/rooms")
@login_required("customer")
def create_room(user):
    """고객이 상담 요청. topic: 카테고리 slug 또는 'school'(학교 상담 신청서 기준)"""
    topic = (request.get_json(silent=True) or {}).get("topic")

    with get_connection() as conn:
        # 이미 대기/진행 중인 상담이 있으면 새로 만들지 않고 그 방을 돌려줌
        open_room = conn.execute(
            ROOM_SELECT + " WHERE r.customer_id = ? AND r.status != 'closed'", (user["id"],)
        ).fetchone()
        if open_room:
            return jsonify(room=room_dict(open_room))

        anonymous = 0
        if topic == "school":
            app_row = conn.execute(
                "SELECT consult_type, anonymous FROM applications WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user["id"],),
            ).fetchone()
            if app_row is None:
                raise ApiError("학교 상담 신청서가 없습니다.")
            names = {t["slug"]: t["name"] for t in CONSULT_TYPES}
            topic_name = f"학교 · {names.get(app_row['consult_type'], '상담')}"
            anonymous = app_row["anonymous"]
        else:
            cat = conn.execute("SELECT name FROM categories WHERE slug = ?", (topic,)).fetchone()
            if cat is None:
                raise ApiError("상담 유형을 선택해 주세요.")
            topic_name = cat["name"]

        cur = conn.execute(
            "INSERT INTO chat_rooms (customer_id, topic, anonymous) VALUES (?, ?, ?)",
            (user["id"], topic_name, anonymous),
        )
        room_id = cur.lastrowid
        add_message(conn, room_id, "상담 요청이 접수되었습니다. 상담원이 곧 연결됩니다.", kind="system")
        room = room_dict(get_room(conn, room_id))

    # with 블록이 끝나면 DB에 저장(commit)된 상태. 이제 알림을 보냄
    socketio.emit("rooms_changed", {"room_id": room_id}, to="agents")
    return jsonify(room=room), 201


@bp.get("/rooms/<int:room_id>/messages")
@login_required()
def room_messages(user, room_id):
    with get_connection() as conn:
        room = get_room(conn, room_id)
        if not can_view(user, room):
            raise ApiError("권한이 없습니다.", 403)
        rows = conn.execute(
            "SELECT * FROM messages WHERE room_id = ? ORDER BY id", (room_id,)
        ).fetchall()
    return jsonify(room=room_dict(room), messages=[message_dict(r) for r in rows])


@bp.post("/rooms/<int:room_id>/accept")
@login_required("agent")
def accept_room(user, room_id):
    with get_connection() as conn:
        # status = 'waiting' 조건: 두 상담원이 동시에 눌러도 한 명만 성공
        cur = conn.execute(
            "UPDATE chat_rooms SET status = 'active', agent_id = ? WHERE id = ? AND status = 'waiting'",
            (user["id"], room_id),
        )
        if cur.rowcount != 1:
            raise ApiError("이미 다른 상담원이 수락했거나 종료된 상담입니다.", 409)
        msg = add_message(conn, room_id, f"{user['nickname']} 상담 선생님이 연결되었습니다.", kind="system")
    emit_message(msg)
    notify_room_changed(room_id)
    return jsonify(ok=True)


@bp.post("/rooms/<int:room_id>/close")
@login_required()
def close_room(user, room_id):
    with get_connection() as conn:
        room = get_room(conn, room_id)
        is_owner = room["customer_id"] == user["id"]
        is_agent = user["role"] == "agent" and room["agent_id"] in (None, user["id"])
        if not (is_owner or is_agent):
            raise ApiError("권한이 없습니다.", 403)
        cur = conn.execute(
            "UPDATE chat_rooms SET status = 'closed', closed_at = datetime('now', 'localtime') "
            "WHERE id = ? AND status != 'closed'",
            (room_id,),
        )
        if cur.rowcount != 1:
            raise ApiError("이미 종료된 상담입니다.", 409)
        who = "고객" if is_owner else "상담원"
        msg = add_message(conn, room_id, f"{who}이 상담을 종료했습니다.", kind="system")
    emit_message(msg)
    notify_room_changed(room_id)
    return jsonify(ok=True)


@bp.get("/summary")
@login_required("agent")
def agent_summary(user):
    """상담원 대시보드 상단 숫자"""
    with get_connection() as conn:
        one = lambda sql, *p: conn.execute(sql, p).fetchone()[0]
        return jsonify(
            waiting=one("SELECT COUNT(*) FROM chat_rooms WHERE status = 'waiting'"),
            active=one("SELECT COUNT(*) FROM chat_rooms WHERE status = 'active' AND agent_id = ?", user["id"]),
            closed_today=one("SELECT COUNT(*) FROM chat_rooms WHERE status = 'closed' AND date(closed_at) = date('now', 'localtime')"),
            pending_charges=one("SELECT COUNT(*) FROM charge_requests WHERE status = 'pending'"),
        )


# ---------------------------------------------------------------------------
# 웹소켓 이벤트
# ---------------------------------------------------------------------------
@socketio.on("connect")
def on_connect(auth=None):
    user = current_user()
    if user is None:
        return False  # 로그인하지 않은 사람은 연결 거부
    join_room(f"user:{user['id']}")
    if user["role"] == "agent":
        join_room("agents")


@socketio.on("join")
def on_join(data):
    """상담방 화면을 열면 그 방의 실시간 메시지를 받기 시작"""
    user = current_user()
    try:
        room_id = int((data or {}).get("room_id"))
        with get_connection() as conn:
            room = get_room(conn, room_id)
    except (TypeError, ValueError, ApiError):
        return {"error": "상담방을 찾을 수 없습니다."}
    if user is None or not can_view(user, room):
        return {"error": "권한이 없습니다."}
    join_room(f"room:{room_id}")
    return {"ok": True}


@socketio.on("send_message")
def on_send_message(data):
    """메시지 전송. 반환값은 보낸 사람에게 '전송 결과'로 전달됨(ack)"""
    user = current_user()
    data = data or {}
    body = str(data.get("body", "")).strip()
    if user is None:
        return {"error": "로그인이 필요합니다."}
    if not body:
        return {"error": "메시지를 입력해 주세요."}
    if len(body) > MAX_MESSAGE:
        return {"error": f"메시지는 {MAX_MESSAGE}자까지 보낼 수 있습니다."}

    try:
        room_id = int(data.get("room_id"))
        with get_connection() as conn:
            room = get_room(conn, room_id)
            if room["status"] == "closed":
                return {"error": "종료된 상담입니다."}
            if user["role"] == "agent":
                if room["agent_id"] != user["id"]:
                    return {"error": "먼저 상담을 수락해 주세요."}
            elif room["customer_id"] != user["id"]:
                return {"error": "권한이 없습니다."}
            msg = add_message(conn, room_id, body, sender_id=user["id"])
    except (TypeError, ValueError, ApiError):
        return {"error": "상담방을 찾을 수 없습니다."}

    emit_message(msg)
    socketio.emit("rooms_changed", {"room_id": room_id}, to="agents")
    return {"ok": True}
