"""
학교 설정 파일: 학교에 맞게 이 파일만 고치면 사이트 전체에 반영됩니다.
"""

GRADES = [1, 2, 3]

CONSULT_TYPES = [
    {"slug": "career", "name": "진로 · 진학", "desc": "대학 진학, 진로 탐색, 적성 고민"},
    {"slug": "study", "name": "학업 · 성적", "desc": "공부 방법, 성적 고민, 수행평가"},
    {"slug": "friends", "name": "교우 관계", "desc": "친구 문제, 학급 생활, 갈등 상담"},
    {"slug": "mind", "name": "심리 · 정서", "desc": "스트레스, 불안, 우울감 등 마음 건강"},
    {"slug": "life", "name": "학교생활 · 기타", "desc": "가정, 생활 습관, 그 밖의 모든 고민"},
]

SCHOOL_INFO = {
    "name": "OO고등학교 Wee클래스",
    # price: 0이면 무료. 0보다 크면 포인트로 결제할 수 있는 유료 서비스
    "fees": [
        {"slug": "chat", "item": "기본 상담 (1:1 채팅)", "price": 0},
        {"slug": "visit", "item": "대면 상담 예약", "price": 0},
        {"slug": "test", "item": "심리검사 (외부 기관 연계)", "price": 10000},
    ],
    "contact": {
        "place": "본관 2층 상담실",
        "phone": "02-000-0000",
        "email": "counsel@school.example",
        "hours": "평일 08:30 ~ 17:00",
    },
}

# 포인트 충전 (무통장입금)
POINT = {
    "min_charge": 1000,          # 최소 충전 금액
    "max_charge": 1_000_000,     # 1회 최대 충전 금액
    "max_pending": 3,            # 입금 대기 중인 신청은 최대 3건까지
    "bank": {"bank": "OO은행", "account": "000-0000-0000-00", "holder": "OO고등학교"},
}
