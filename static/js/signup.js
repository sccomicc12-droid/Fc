renderHeader();

document.getElementById("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorBox = document.getElementById("form-error");
  const data = Object.fromEntries(new FormData(e.target));

  // 프론트에서 먼저 검사하면 서버에 보내기 전에 빠르게 알려줄 수 있음 (서버도 다시 검사함)
  if (data.password !== data.password2) {
    errorBox.textContent = "비밀번호가 서로 다릅니다.";
    return;
  }
  errorBox.textContent = "";
  try {
    await api("/api/signup", data);
    // 가입 성공 후 바로 로그인 처리
    await api("/api/login", { username: data.username, password: data.password });
    location.href = "/customer";
  } catch (err) {
    errorBox.textContent = err.message;
  }
});
