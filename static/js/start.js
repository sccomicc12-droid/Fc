// 학교 상담 신청: 1) 학년 선택 → 2) 신청서 작성 → 3) 완료
let info = null;      // 서버에서 받은 학교 정보 (상담 유형, 요금, 연락처)
let grade = null;     // 선택한 학년

const views = {
  grade: document.getElementById("step-grade"),
  form: document.getElementById("step-form"),
  done: document.getElementById("step-done"),
};

// 원하는 단계만 보이고 나머지는 숨김
function showStep(name) {
  const order = ["grade", "form", "done"];
  Object.entries(views).forEach(([key, el]) => (el.hidden = key !== name));
  document.querySelectorAll("#progress li").forEach((li, i) => {
    const current = order.indexOf(name);
    li.classList.toggle("active", i === current);
    li.classList.toggle("done", i < current);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

(async () => {
  renderHeader();
  info = await api("/api/school/info");

  // 1단계: 학년 카드
  document.getElementById("grade-grid").innerHTML = info.grades.map((g) => `
    <button type="button" class="grade-card" data-grade="${g}">
      <span class="grade-num">${g}</span><span>학년</span>
    </button>`).join("");

  // 상담 유형 5개
  document.getElementById("type-grid").innerHTML = info.consult_types.map((t) => `
    <label class="choice type-choice">
      <input type="radio" name="consult_type" value="${escapeHtml(t.slug)}">
      <span><i class="icon">${icon(t.slug)}</i><b>${escapeHtml(t.name)}</b><small>${escapeHtml(t.desc)}</small></span>
    </label>`).join("");

  // 요금표, 연락처
  document.getElementById("fee-table").innerHTML = info.fees.map((f) => `
    <tr><td>${escapeHtml(f.item)}</td><td class="${f.price === 0 ? "mint" : ""}">${f.price === 0 ? "무료" : `1회 ${won(f.price)}`}</td></tr>`).join("");
  document.getElementById("contact").innerHTML = contactHtml(info);
})();

function contactHtml(info) {
  const c = info.contact;
  return `
    <dt>기관</dt><dd>${escapeHtml(info.name)}</dd>
    <dt>위치</dt><dd>${escapeHtml(c.place)}</dd>
    <dt>전화</dt><dd><a class="mint" href="tel:${escapeHtml(c.phone)}">${escapeHtml(c.phone)}</a></dd>
    <dt>이메일</dt><dd>${escapeHtml(c.email)}</dd>
    <dt>운영 시간</dt><dd>${escapeHtml(c.hours)}</dd>`;
}

// 학년 선택
document.getElementById("grade-grid").addEventListener("click", (e) => {
  const card = e.target.closest(".grade-card");
  if (!card) return;
  grade = Number(card.dataset.grade);
  document.getElementById("grade-badge").textContent = `${grade}학년`;
  showStep("form");
});
document.getElementById("change-grade").addEventListener("click", () => showStep("grade"));

// 전화번호 자동 하이픈: 01012345678 → 010-1234-5678
document.getElementById("phone").addEventListener("input", (e) => {
  const d = e.target.value.replace(/\D/g, "").slice(0, 11);
  e.target.value = d.length < 4 ? d : d.length < 8 ? `${d.slice(0, 3)}-${d.slice(3)}`
    : `${d.slice(0, 3)}-${d.slice(3, d.length - 4)}-${d.slice(-4)}`;
});

// 개인정보 '아니요' 선택 시 경고 + 신청 버튼 잠금
document.querySelectorAll('input[name="privacy_agree"]').forEach((r) =>
  r.addEventListener("change", () => {
    const no = r.value === "no" && r.checked;
    document.getElementById("privacy-warn").hidden = !no;
    document.getElementById("submit-btn").disabled = no;
  }));

// 신청서 제출
views.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorBox = document.getElementById("form-error");
  const data = Object.fromEntries(new FormData(e.target));
  data.grade = grade;

  // 빠뜨린 항목을 먼저 알려줌 (서버도 다시 검사함)
  const missing = [
    ["real_name", "이름"], ["phone", "전화번호"], ["username", "아이디"],
    ["school_code", "학교 코드"], ["password", "비밀번호"],
    ["consult_type", "상담 유형"], ["anonymous", "익명 여부"], ["privacy_agree", "개인정보 동의"],
  ].filter(([key]) => !data[key]).map(([, label]) => label);
  if (missing.length) {
    errorBox.textContent = `${missing.join(", ")}을(를) 입력하거나 선택해 주세요.`;
    return;
  }
  if (data.password !== data.password2) {
    errorBox.textContent = "비밀번호가 서로 다릅니다.";
    return;
  }

  errorBox.textContent = "";
  const btn = document.getElementById("submit-btn");
  btn.disabled = true;
  btn.textContent = "신청 중...";
  try {
    await api("/api/school/apply", data);
    showDone(data);
  } catch (err) {
    errorBox.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "신청하기";
  }
});

function showDone(data) {
  const type = info.consult_types.find((t) => t.slug === data.consult_type);
  const ratingText = ["", "매우 불만족", "불만족", "보통", "만족", "매우 만족"][data.satisfaction] || "선택 안 함";
  document.getElementById("done-text").textContent =
    `${data.real_name}님의 신청이 접수되었어요. 상담 선생님이 곧 연락드립니다.`;
  document.getElementById("summary").innerHTML = `
    <dt>학년</dt><dd>${grade}학년</dd>
    <dt>상담 유형</dt><dd>${escapeHtml(type.name)}</dd>
    <dt>익명 여부</dt><dd>${data.anonymous === "yes" ? "익명" : "실명"}</dd>
    <dt>만족도</dt><dd>${ratingText}</dd>`;
  document.getElementById("done-contact").textContent =
    `문의: ${info.name} ${info.contact.phone} (${info.contact.hours})`;
  renderHeader(); // 로그인 상태로 헤더 갱신
  showStep("done");
}
