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

학교 이름, 상담 유형, 이용 요금, 연락처는 `app.py` 위쪽의 `CONSULT_TYPES`, `SCHOOL_INFO`에서 바꿀 수 있습니다.

## 진행 상황
- [x] 1단계: DB, 회원가입·로그인 API
- [x] 2단계: 고객/상담원 화면 (다크 + 민트 디자인)
- [x] 2-1단계: 학교 상담 신청 (학년 선택, 학교 코드, 익명·개인정보 동의, 만족도)
- [ ] 3단계: 실시간 1:1 채팅
- [ ] 4단계: 마무리 및 발표 정리
