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
