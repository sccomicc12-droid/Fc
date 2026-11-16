-- 회원 테이블
-- role: 'customer'(고객) 또는 'agent'(상담원)
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,      -- 로그인 아이디 (중복 불가)
    password_hash TEXT    NOT NULL,             -- 비밀번호는 절대 그대로 저장하지 않고 해시로 저장
    nickname      TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'customer',
    real_name     TEXT,                         -- 실명 (학교 신청으로 가입한 경우)
    phone         TEXT,
    grade         INTEGER,                      -- 학년 (1~3)
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 문의 카테고리 테이블 (주문·배송, 결제·환불 ...)
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT    NOT NULL UNIQUE,   -- 주소에 쓰는 영문 이름 (예: order)
    name        TEXT    NOT NULL,          -- 화면에 보이는 이름
    description TEXT    NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- 학교에서 학생에게 나눠준 가입 코드. 한 코드는 한 명만 사용 가능
CREATE TABLE IF NOT EXISTS school_codes (
    code    TEXT PRIMARY KEY,
    used_by INTEGER REFERENCES users(id),   -- 아직 안 쓴 코드는 NULL
    used_at TEXT
);

-- 학교 상담 신청서
CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    grade         INTEGER NOT NULL,
    consult_type  TEXT    NOT NULL,
    anonymous     INTEGER NOT NULL,          -- 1 = 익명, 0 = 실명
    privacy_agree INTEGER NOT NULL,          -- 1 = 동의 (동의해야만 저장됨)
    satisfaction  INTEGER,                   -- 1~5점, 선택 안 하면 NULL
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 1:1 상담방. status: waiting(대기) → active(상담 중) → closed(종료)
CREATE TABLE IF NOT EXISTS chat_rooms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES users(id),
    agent_id    INTEGER REFERENCES users(id),     -- 수락한 상담원 (대기 중이면 NULL)
    topic       TEXT    NOT NULL,                 -- 상담 주제 이름 (예: 학교 · 심리 · 정서)
    anonymous   INTEGER NOT NULL DEFAULT 0,       -- 1이면 상담원에게 '익명 학생'으로 표시
    status      TEXT    NOT NULL DEFAULT 'waiting',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    closed_at   TEXT
);

-- 채팅 메시지. kind: text(일반) / system(연결됨, 종료됨 같은 안내)
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id    INTEGER NOT NULL REFERENCES chat_rooms(id),
    sender_id  INTEGER REFERENCES users(id),      -- 시스템 메시지는 NULL
    kind       TEXT    NOT NULL DEFAULT 'text',
    body       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id, id);

-- 포인트 충전 신청 (무통장입금). status: pending(입금 대기) / approved(적립 완료) / rejected(반려)
CREATE TABLE IF NOT EXISTS charge_requests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    amount       INTEGER NOT NULL CHECK (amount >= 1000),   -- DB에서도 최소 금액을 한 번 더 보장
    depositor    TEXT    NOT NULL,                          -- 입금자명
    status       TEXT    NOT NULL DEFAULT 'pending',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    processed_at TEXT,
    processed_by INTEGER REFERENCES users(id)
);

-- 포인트 장부: 적립은 +, 사용은 -. 잔액 = 이 사용자의 amount 합계
-- (잔액 숫자 하나만 저장하지 않고 모든 내역을 남기는 것이 실제 결제 시스템의 기본 방식)
CREATE TABLE IF NOT EXISTS point_ledger (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    amount     INTEGER NOT NULL,
    reason     TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
