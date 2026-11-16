renderHeader();

// 로그인 후 돌아갈 주소 (예: /login?next=/customer). 다른 사이트로 튕기지 않게 "/"로 시작하는지 확인
function nextUrl(role) {
  const next = new URLSearchParams(location.search).get("next");
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return role === "agent" ? "/agent" : "/customer";
}

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault(); // 페이지 새로고침 막기
  const errorBox = document.getElementById("form-error");
  errorBox.textContent = "";
  try {
    const { user } = await api("/api/login", Object.fromEntries(new FormData(e.target)));
    location.href = nextUrl(user.role);
  } catch (err) {
    errorBox.textContent = err.message;
  }
});
