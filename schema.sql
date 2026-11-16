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
