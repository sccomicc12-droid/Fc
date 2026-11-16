// 모든 페이지에서 같이 쓰는 함수 모음

// 백엔드 API 호출: body가 있으면 POST, 없으면 GET
async function api(url, body) {
  const res = await fetch(url, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "요청에 실패했습니다.");
  return data;
}

// 사용자가 입력한 글자를 HTML로 그대로 넣으면 XSS 공격이 가능하므로 변환
function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

// 화면 아래에 잠깐 뜨는 알림
function toast(text, type = "") {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.className = `toast show ${type}`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 2500);
}

// 카테고리별 아이콘 (SVG 선 아이콘)
const ICONS = {
  order: '<path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7"/><path d="M12 11v10"/>',
  payment: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/><path d="M6 15h4"/>',
  account: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
  product: '<path d="M20 12l-8 8-9-9V3h8l9 9z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  tech: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.5-.5-.5-2.5 2.5-2.5z"/>',
  etc: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z"/><path d="M8 11h8M8 14h5"/>',
  start: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l5 3.5-5 3.5z"/>',
  // 학교 상담 유형
  career: '<path d="M22 10L12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 2 9 2 12 0v-5"/>',
  study: '<path d="M4 4h6a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2H4z"/><path d="M20 4h-6a2 2 0 0 0-2 2v14a2 2 0 0 1 2-2h6z"/>',
  friends: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M19 14.8c1.8.8 3 2.4 3 5.2"/>',
  mind: '<path d="M12 21s-8-5-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 6-8 11-8 11z"/>',
  life: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
};
function icon(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
    stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ICONS.etc}</svg>`;
}

// 상단 헤더를 그리고, 현재 로그인한 사용자를 돌려줌
async function renderHeader() {
  const header = document.getElementById("site-header");
  let user = null;
  try {
    ({ user } = await api("/api/me"));
  } catch (_) { /* 서버 오류 시 비로그인으로 처리 */ }

  let nav;
  if (user) {
    const isAgent = user.role === "agent";
    nav = `
      <span class="user-chip"><span class="status-dot on"></span>${escapeHtml(user.nickname)}
        <span class="badge ${isAgent ? "" : "badge-gray"}">${isAgent ? "상담원" : "고객"}</span></span>
      <a class="btn btn-outline" href="${isAgent ? "/agent" : "/customer"}">${isAgent ? "대시보드" : "내 상담"}</a>
      <button class="btn btn-ghost" id="logout-btn">로그아웃</button>`;
  } else {
    nav = `
      <a class="btn btn-ghost" href="/login">로그인</a>
      <a class="btn btn-mint" href="/signup">회원가입</a>`;
  }

  header.className = "site-header";
  header.innerHTML = `
    <div class="container">
      <a class="logo" href="/"><span class="logo-mark">M</span>MintDesk</a>
      <nav class="nav">${nav}</nav>
    </div>`;

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.onclick = async () => {
      await api("/api/logout", {});
      location.href = "/";
    };
  }
  return user;
}
