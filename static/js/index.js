// 메인 페이지: 카테고리 목록을 서버(DB)에서 받아 카드로 그립니다.
(async () => {
  const user = await renderHeader();
  if (user && user.role === "agent") {
    document.getElementById("hero-actions").innerHTML =
      '<a class="btn btn-mint" href="/agent">상담원 대시보드로 이동</a>';
  }

  const { categories } = await api("/api/categories");
  // 첫 번째 칸은 학교 상담 신청 "시작하기" 카드
  const startCard = `
    <a class="category-card category-start" href="/start">
      <span class="icon">${icon("start")}</span>
      <span class="badge">학생 전용</span>
      <h3>시작하기</h3>
      <p>학년 선택부터 시작하는 우리 학교 상담 신청</p>
    </a>`;
  document.getElementById("category-grid").innerHTML = startCard + categories.map((c) => `
    <a class="category-card" href="/customer?category=${encodeURIComponent(c.slug)}">
      <span class="icon">${icon(c.slug)}</span>
      <span class="arrow">→</span>
      <h3>${escapeHtml(c.name)}</h3>
      <p>${escapeHtml(c.description)}</p>
    </a>`).join("");
})();
