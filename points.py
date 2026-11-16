"""
포인트 충전 (무통장입금 방식)

1) 학생이 금액과 입금자명을 적어 충전 신청 → status = pending(입금 대기)
2) 학생이 안내된 학교 계좌로 이체
3) 상담원(관리자)이 통장을 확인하고 '입금 확인' → status = approved, 포인트 장부에 +금액
4) 학생은 포인트로 유료 서비스(심리검사 등)를 결제 → 포인트 장부에 -금액

※ 실제 은행과 자동 연동하려면 PG사(토스페이먼츠 등) 계약이 필요해서,
   학교 과제에서는 관리자가 직접 입금을 확인하는 방식으로 구현했습니다.
"""
from flask import Blueprint, jsonify, request

from config import POINT, SCHOOL_INFO
from database import get_connection
from helpers import ApiError, login_required, socketio

bp = Blueprint("points", __name__, url_prefix="/api")

STATUS_TEXT = {"pending": "입금 대기", "approved": "적립 완료", "rejected": "반려"}


def get_balance(conn, user_id):
    """잔액 = 장부(point_ledger)에 적힌 금액을 모두 더한 값"""
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM point_ledger WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


def paid_products():
    """요금표 중 가격이 0보다 큰 것 = 포인트로 결제하는 유료 서비스"""
    return [f for f in SCHOOL_INFO["fees"] if f["price"] > 0]


def charge_dict(row):
    d = {k: row[k] for k in ("id", "amount", "depositor", "status", "created_at", "processed_at")}
    d["status_text"] = STATUS_TEXT[row["status"]]
    for extra in ("username", "nickname", "real_name"):
        if extra in row.keys():
            d[extra] = row[extra]
    return d


# ---------------------------------------------------------------------------
# 학생(고객)용
# ---------------------------------------------------------------------------
@bp.get("/points")
@login_required("customer")
def my_points(user):
    with get_connection() as conn:
        ledger = conn.execute(
            "SELECT amount, reason, created_at FROM point_ledger WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user["id"],),
        ).fetchall()
        charges = conn.execute(
            "SELECT * FROM charge_requests WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user["id"],)
        ).fetchall()
        balance = get_balance(conn, user["id"])
    return jsonify(
        balance=balance,
        ledger=[dict(r) for r in ledger],
        charges=[charge_dict(r) for r in charges],
        products=paid_products(),
        bank=POINT["bank"],
        min_charge=POINT["min_charge"],
        max_charge=POINT["max_charge"],
    )


@bp.post("/points/charge")
@login_required("customer")
def request_charge(user):
    d = request.get_json(silent=True) or {}
    depositor = (d.get("depositor") or "").strip()
    try:
        amount = int(d.get("amount"))
    except (TypeError, ValueError):
        raise ApiError("충전 금액을 숫자로 입력해 주세요.")

    if amount < POINT["min_charge"]:
        raise ApiError(f"최소 충전 금액은 {POINT['min_charge']:,}원입니다.")
    if amount > POINT["max_charge"]:
        raise ApiError(f"1회 최대 충전 금액은 {POINT['max_charge']:,}원입니다.")
    if not 2 <= len(depositor) <= 20:
        raise ApiError("입금자명을 2~20자로 입력해 주세요.")

    with get_connection() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) FROM charge_requests WHERE user_id = ? AND status = 'pending'", (user["id"],)
        ).fetchone()[0]
        if pending >= POINT["max_pending"]:
            raise ApiError(f"입금 대기 중인 신청이 {POINT['max_pending']}건 있습니다. 먼저 입금해 주세요.")
        cur = conn.execute(
            "INSERT INTO charge_requests (user_id, amount, depositor) VALUES (?, ?, ?)",
            (user["id"], amount, depositor),
        )
        charge = charge_dict(conn.execute("SELECT * FROM charge_requests WHERE id = ?", (cur.lastrowid,)).fetchone())

    socketio.emit("charges_changed", {}, to="agents")  # 상담원 화면에 새 입금 신청 알림
    return jsonify(charge=charge, bank=POINT["bank"]), 201


@bp.post("/points/use")
@login_required("customer")
def use_points(user):
    slug = (request.get_json(silent=True) or {}).get("product")
    product = next((p for p in paid_products() if p["slug"] == slug), None)
    if product is None:
        raise ApiError("결제할 서비스를 찾을 수 없습니다.")

    with get_connection() as conn:
        # BEGIN IMMEDIATE: 잔액 확인~차감이 끝날 때까지 다른 쓰기를 막아
        # 같은 포인트를 두 번 쓰는 일(동시 결제)을 방지
        conn.execute("BEGIN IMMEDIATE")
        balance = get_balance(conn, user["id"])
        if balance < product["price"]:
            raise ApiError(f"포인트가 부족합니다. ({product['price'] - balance:,}P 부족)")
        conn.execute(
            "INSERT INTO point_ledger (user_id, amount, reason) VALUES (?, ?, ?)",
            (user["id"], -product["price"], f"{product['item']} 결제"),
        )
        balance -= product["price"]

    return jsonify(message=f"{product['item']} 결제가 완료되었습니다.", balance=balance)


# ---------------------------------------------------------------------------
# 상담원(관리자)용
# ---------------------------------------------------------------------------
@bp.get("/admin/charges")
@login_required("agent")
def admin_charges(user):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT c.*, u.username, u.nickname, u.real_name
               FROM charge_requests c JOIN users u ON u.id = c.user_id
               ORDER BY c.status != 'pending', c.id DESC LIMIT 30"""
        ).fetchall()
    return jsonify(charges=[charge_dict(r) for r in rows])


def process_charge(agent, charge_id, approve):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM charge_requests WHERE id = ?", (charge_id,)).fetchone()
        if row is None:
            raise ApiError("충전 신청을 찾을 수 없습니다.", 404)
        # status = 'pending' 조건: 같은 신청을 두 번 승인해서 포인트가 두 번 쌓이는 것을 방지
        cur = conn.execute(
            "UPDATE charge_requests SET status = ?, processed_at = datetime('now', 'localtime'), processed_by = ? "
            "WHERE id = ? AND status = 'pending'",
            ("approved" if approve else "rejected", agent["id"], charge_id),
        )
        if cur.rowcount != 1:
            raise ApiError("이미 처리된 신청입니다.", 409)
        if approve:
            conn.execute(
                "INSERT INTO point_ledger (user_id, amount, reason) VALUES (?, ?, ?)",
                (row["user_id"], row["amount"], f"계좌이체 충전 (입금자 {row['depositor']})"),
            )
        balance = get_balance(conn, row["user_id"])

    # 해당 학생 화면에 실시간으로 잔액 갱신
    socketio.emit("points_changed", {"balance": balance, "approved": approve, "amount": row["amount"]},
                  to=f"user:{row['user_id']}")
    socketio.emit("charges_changed", {}, to="agents")
    return jsonify(ok=True)


@bp.post("/admin/charges/<int:charge_id>/approve")
@login_required("agent")
def approve_charge(user, charge_id):
    return process_charge(user, charge_id, approve=True)


@bp.post("/admin/charges/<int:charge_id>/reject")
@login_required("agent")
def reject_charge(user, charge_id):
    return process_charge(user, charge_id, approve=False)
