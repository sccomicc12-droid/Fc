// 상담원 화면: 카테고리별 대기 현황 (실제 숫자와 고객 목록은 3단계에서 실시간으로 채움)
(async () => {
  await renderHeader();
  document.getElementById("empty-icon").innerHTML = icon("inbox");

  const { categories } = await api("/api/categories");
  document.getElementById("stats").innerHTML = categories.map((c) => `
    <div class="stat" data-slug="${escapeHtml(c.slug)}">
      <div class="label">${icon(c.slug)}${escapeHtml(c.name)}</div>
      <div class="num">0</div>
    </div>`).join("");
})();
