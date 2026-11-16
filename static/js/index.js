// 메인 페이지: 카테고리 목록을 서버(DB)에서 받아 카드로 그립니다.
(async () => {
  const user = await renderHeader();
  if (user && user.role === "agent") {
    document.getElementById("hero-actions").innerHTML =
      '<a class="btn btn-mint" href="/agent">상담원 대시보드로 이동</a>';
  }

  const { categories } = await api("/api/categories");
  document.getElementById("category-grid").innerHTML = categories.map((c) => `
    <a class="category-card" href="/customer?category=${encodeURIComponent(c.slug)}">
      <span class="icon">${icon(c.slug)}</span>
      <span class="arrow">→</span>
      <h3>${escapeHtml(c.name)}</h3>
      <p>${escapeHtml(c.description)}</p>
    </a>`).join("");
})();
