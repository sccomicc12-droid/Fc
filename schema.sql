-- 회원 테이블
-- role: 'customer'(고객) 또는 'agent'(상담원)
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,      -- 로그인 아이디 (중복 불가)
    password_hash TEXT    NOT NULL,             -- 비밀번호는 절대 그대로 저장하지 않고 해시로 저장
    nickname      TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'customer',
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
