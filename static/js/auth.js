// 프론트엔드: 사용자의 입력을 받아 fetch()로 백엔드 API에 보내고, 결과를 화면에 그립니다.

const message = document.getElementById("message");
const statusBox = document.getElementById("status");

// 공통 API 호출 함수: JSON을 보내고 JSON을 받습니다.
async function api(url, body) {
  const res = await fetch(url, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "요청 실패");
  return data;
}

function show(text, type) {
  message.textContent = text;
  message.className = type;
}

// <form>의 입력값을 { username: "...", password: "..." } 객체로 바꿉니다.
const formToObject = (form) => Object.fromEntries(new FormData(form));

// 로그인 상태를 서버에 물어보고 화면에 표시
async function refreshStatus() {
  const { user } = await api("/api/me");
  if (user) {
    const roleText = user.role === "agent" ? "상담원" : "고객";
    statusBox.innerHTML = `<b>${escapeHtml(user.nickname)}</b>님 (${roleText}) 로그인 중
      <button id="logout-btn">로그아웃</button>`;
    document.getElementById("logout-btn").onclick = async () => {
      await api("/api/logout", {});
      show("로그아웃되었습니다.", "success");
      refreshStatus();
    };
  } else {
    statusBox.textContent = "로그인하지 않은 상태입니다.";
  }
}

document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault(); // 페이지 새로고침 막기
  try {
    const data = await api("/api/signup", formToObject(e.target));
    show(data.message, "success");
    e.target.reset();
  } catch (err) {
    show(err.message, "error");
  }
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const { user } = await api("/api/login", formToObject(e.target));
    show(`${user.nickname}님 환영합니다!`, "success");
    e.target.reset();
    refreshStatus();
  } catch (err) {
    show(err.message, "error");
  }
});

// 사용자가 입력한 글자를 HTML로 그대로 넣으면 XSS 공격이 가능하므로 변환합니다.
function escapeHtml(str) {
  return str.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

refreshStatus();
