// 입력 폼 UI 패턴 예제
// 포인트: 1) 입력하는 즉시 피드백  2) 제출 전 프론트 검사  3) 서버가 다시 검사한 값 표시

renderHeader();

const $ = (id) => document.getElementById(id);

// ----- 1) 실시간 글자 수 -----
function bindCounter(inputId, counterId, max) {
  const input = $(inputId), counter = $(counterId);
  const update = () => (counter.textContent = `${input.value.length} / ${max}`);
  input.addEventListener("input", update);
  update();
}
bindCounter("name", "name-count", 20);
bindCounter("message", "message-count", 300);

// ----- 2) 이메일 형식 통과 시 체크 표시 -----
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
$("email").addEventListener("input", (e) => {
  $("email-ok").hidden = !EMAIL_RE.test(e.target.value.trim());
});

// ----- 3) 비밀번호 강도 미터 (화면 안내용, 서버로 보내지 않음) -----
$("reveal").addEventListener("click", () => {
  const pw = $("password");
  const show = pw.type === "password";
  pw.type = show ? "text" : "password";
  $("reveal").textContent = show ? "숨김" : "보기";
});
$("password").addEventListener("input", (e) => {
  const v = e.target.value;
  // 길이, 영문, 숫자, 기호 중 몇 가지를 만족하는지로 0~4점 계산
  let score = 0;
  if (v.length >= 8) score++;
  if (/[a-zA-Z]/.test(v)) score++;
  if (/[0-9]/.test(v)) score++;
  if (/[^a-zA-Z0-9]/.test(v)) score++;
  const levels = ["", "약함", "보통", "좋음", "아주 좋음"];
  const colors = ["", "#ff6b81", "#f5c451", "#7dd3c0", "#3ef0c8"];
  const bar = $("meter-bar");
  bar.style.width = `${(score / 4) * 100}%`;
  bar.style.background = colors[score] || "transparent";
  $("pw-hint").textContent = v ? `강도: ${levels[score]}` : "8자 이상을 권장해요";
});

// ----- 6) 숫자 스테퍼 (+/- 버튼) -----
document.querySelectorAll(".stepper button[data-step]").forEach((btn) =>
  btn.addEventListener("click", () => {
    const input = $("headcount");
    const next = (Number(input.value) || 0) + Number(btn.dataset.step);
    input.value = Math.min(100, Math.max(1, next)); // 1~100 범위로 묶음
  }));

// ----- 오류 표시 도우미 -----
function clearErrors() {
  document.querySelectorAll("[data-err]").forEach((el) => (el.textContent = ""));
  document.querySelectorAll(".input, select, textarea").forEach((el) => el.classList.remove("invalid"));
  $("form-error").textContent = "";
}
function showErrors(fields) {
  Object.entries(fields).forEach(([name, msg]) => {
    const box = document.querySelector(`[data-err="${name}"]`);
    if (box) box.textContent = msg;
    const input = document.querySelector(`[name="${name}"], #${name}`);
    if (input) input.classList.add("invalid");
  });
}

// ----- 제출 -----
$("demo-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearErrors();

  // 폼 값을 객체로 모음 (체크박스 channels는 여러 개라 배열로)
  const form = e.target;
  const data = {
    name: form.name.value.trim(),
    email: form.email.value.trim(),
    topic: form.topic.value,
    visit_date: form.visit_date.value,
    headcount: form.headcount.value,
    channels: [...form.querySelectorAll('input[name="channels"]:checked')].map((c) => c.value),
    message: form.message.value.trim(),
    agree: form.agree.checked,
  };

  const btn = $("submit-btn");
  btn.disabled = true;
  btn.textContent = "전송 중...";
  try {
    const res = await api("/api/demo/echo", data);
    // 서버가 돌려준 '정리된 값'을 보기 좋게 출력
    $("result").textContent = JSON.stringify(res.received, null, 2);
    $("result-note").innerHTML = '<span class="ok-note">✓ 서버 검사를 통과했어요</span>';
    toast("제출 완료! 서버가 받은 값을 확인하세요.");
  } catch (err) {
    // api()는 서버가 400을 주면 메시지를 throw. 자세한 필드 오류는 따로 받아서 표시
    const detail = err.fields;
    if (detail) showErrors(detail);
    $("form-error").textContent = err.message;
    $("result-note").innerHTML = '<span class="bad-note">✗ 검사에서 막혔어요. 빨간 안내를 확인하세요</span>';
  } finally {
    btn.disabled = false;
    btn.textContent = "제출하기";
  }
});
