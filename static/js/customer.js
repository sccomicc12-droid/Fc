// 고객 화면: 카테고리를 고르고 상담을 시작 (실시간 채팅 연결은 3단계에서)
let selected = null;

(async () => {
  const user = await renderHeader();
  document.getElementById("greeting").textContent = `${user.nickname}님, 안녕하세요`;
  document.getElementById("empty-icon").innerHTML = icon("chat");

  const { categories } = await api("/api/categories");
  const list = document.getElementById("category-list");
  list.innerHTML = categories.map((c) => `
    <button class="side-item" data-slug="${escapeHtml(c.slug)}">
      <span class="icon">${icon(c.slug)}</span>
      <span><b>${escapeHtml(c.name)}</b><small>${escapeHtml(c.description)}</small></span>
    </button>`).join("");

  list.addEventListener("click", (e) => {
    const item = e.target.closest(".side-item");
    if (!item) return;
    select(categories.find((c) => c.slug === item.dataset.slug));
  });

  // 메인 페이지에서 카테고리를 눌러 들어온 경우 미리 선택
  const fromUrl = new URLSearchParams(location.search).get("category");
  const initial = categories.find((c) => c.slug === fromUrl);
  if (initial) select(initial);
})();

function select(category) {
  selected = category;
  document.querySelectorAll(".side-item").forEach((el) =>
    el.classList.toggle("active", el.dataset.slug === category.slug));
  document.getElementById("chat-title").textContent = category.name;
  document.getElementById("chat-status").textContent = "상담 시작 버튼을 눌러주세요";
  document.getElementById("start-btn").disabled = false;
}

document.getElementById("start-btn").addEventListener("click", () => {
  toast("실시간 채팅은 3단계에서 연결됩니다!");
});
