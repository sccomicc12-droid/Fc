# 고객센터 웹사이트 (웹 개발 동아리 과제)

회원가입/로그인과 실시간 1:1 상담 채팅이 가능한 고객센터 모의 사이트입니다.

- 프론트엔드: HTML / CSS / JavaScript (`fetch` API)
- 백엔드: Python Flask + SQLite

## 실행 방법
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   /  Mac·Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
브라우저에서 http://localhost:5000 접속

테스트 상담원 계정: `agent` / `agent1234`
테스트 학교 코드: `MINT-1001` ~ `MINT-1010` (코드 하나당 한 명만 가입 가능)

학교 이름, 상담 유형, 이용 요금, 연락처, 입금 계좌는 `config.py`에서 바꿀 수 있습니다.

## 진행 상황
- [x] 1단계: DB, 회원가입·로그인 API
- [x] 2단계: 고객/상담원 화면 (다크 + 민트 디자인)
- [x] 2-1단계: 학교 상담 신청 (학년 선택, 학교 코드, 익명·개인정보 동의, 만족도)
- [x] 3단계: 실시간 1:1 채팅 (Socket.IO)
- [x] 3-1단계: 포인트 충전(무통장입금) · 관리자 입금 확인 · 포인트 결제
- [ ] 4단계: 마무리 및 발표 정리

## 파일 구조
| 파일 | 역할 |
|---|---|
| `app.py` | 서버 시작, 페이지, 회원가입/로그인, 학교 상담 신청 |
| `chat.py` | 실시간 1:1 상담 (REST API + 웹소켓 이벤트) |
| `points.py` | 포인트 충전 신청, 입금 확인, 포인트 결제 |
| `helpers.py` | 공통 함수 (로그인 확인 데코레이터, 오류 처리) |
| `config.py` | 학교 설정 |
| `database.py`, `schema.sql` | DB 생성과 테이블 정의 |
| `pages/` | HTML 화면 |
| `static/` | CSS, JavaScript |
