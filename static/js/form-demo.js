// 상담 신청서 모양의 입력 폼 UI 예제
// 포인트: 1) 세그먼트 토글 선택  2) 실시간 요금 계산  3) 약관 전체동의  4) 제출 후 서버가 받은 값 표시

renderHeader();
const $ = (id) => document.getElementById(id);
// won()은 common.js에 이미 정의되어 있어서 여기서 다시 선언하지 않습니다.

// 현재 선택 상태 (세그먼트 토글)
const state = { service: "basic", priority: "off", coupon: "none" };
const PRICE = { basic: 900, focus: 3000, report: 5000 };
const PRIORITY_FEE = 1000;
const COUPON_DISCOUNT = 500;

// ----- 1) 세그먼트 토글: 버튼 하나만 active -----
document.querySelectorAll(".seg").forEach((seg) => {
  const name = seg.dataset.name;
  seg.addEventListener("click", (e) => {
    const btn = e.target.closest(".seg-btn");
    if (!btn) return;
    seg.querySelectorAll(".seg-btn").forEach((b) => b.classList.toggle("active", b === btn));
    state[name] = btn.dataset.value;
    recalc();
  });
});

// ----- 2) 실시간 총 요금 계산 -----
function recalc() {
  const base = PRICE[state.service];
  let total = base;

  $("base-fee").textContent = won(base);

  const priorityOn = state.priority === "on";
  $("priority-row").hidden = !priorityOn;
  if (priorityOn) total += PRIORITY_FEE;

  const couponOn = state.coupon === "use";
  $("coupon-row").hidden = !couponOn;
  if (couponOn) total = Math.max(0, total - COUPON_DISCOUNT);

  $("total-fee").textContent = won(total);
  $("deposit-amount").textContent = won(total);
}
recalc();

// 전화번호 자동 하이픈
$("phone").addEventListener("input", (e) => {
  const d = e.target.value.replace(/\D/g, "").slice(0, 11);
  e.target.value = d.length < 4 ? d : d.length < 8 ? `${d.slice(0, 3)}-${d.slice(3)}`
    : `${d.slice(0, 3)}-${d.slice(3, d.length - 4)}-${d.slice(-4)}`;
});

// ----- 3) 약관: 전체 동의 <-> 개별 체크 연동 -----
const agreeBoxes = [...document.querySelectorAll('.term input[type="checkbox"]')];
const agreeAll = $("agree-all");
agreeAll.addEventListener("change", () => agreeBoxes.forEach((c) => (c.checked = agreeAll.checked)));
agreeBoxes.forEach((c) => c.addEventListener("change", () => {
  agreeAll.checked = agreeBoxes.every((b) => b.checked);
}));
// 약관 제목을 누르면 설명이 접혔다 펴짐
document.querySelectorAll(".term .choice-check span").forEach((title) =>
  title.addEventListener("click", (e) => {
    if (e.target.tagName === "INPUT") return;
    title.closest(".term").classList.toggle("open");
  }));

// ----- 4) 계좌 복사 -----
async function copyAccount() {
  try {
    await navigator.clipboard.writeText($("acc-text").textContent.trim());
    toast("계좌 정보를 복사했어요.");
  } catch (_) {
    toast("복사에 실패했어요. 직접 입력해 주세요.", "error");
  }
}
$("acc-copy").addEventListener("click", copyAccount);
$("tab-copy").addEventListener("click", copyAccount);

// 하단 탭바(예제용): 눌러도 실제 이동은 안 하고 안내만
document.querySelectorAll(".tabbar button[data-tab]").forEach((b) => {
  if (b.id === "tab-copy") return;
  b.addEventListener("click", () => toast(`"${b.dataset.tab}"은(는) 예제라 동작하지 않아요.`));
});
$("history-btn").addEventListener("click", () => toast("신청 내역은 예제라 비어 있어요."));

// ----- 오류 표시 -----
function clearErrors() {
  document.querySelectorAll("[data-err]").forEach((el) => (el.textContent = ""));
  document.querySelectorAll(".input").forEach((el) => el.classList.remove("invalid"));
  $("form-error").textContent = "";
}
function showErrors(fields) {
  Object.entries(fields).forEach(([name, msg]) => {
    const box = document.querySelector(`[data-err="${name}"]`);
    if (box) box.textContent = msg;
    const input = document.querySelector(`#${name}`);
    if (input) input.classList.add("invalid");
  });
}

// ----- 제출 -----
$("demo-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearErrors();

  const data = {
    name: $("name").value.trim(),
    phone: $("phone").value.trim(),
    service: state.service,
    priority: state.priority,
    coupon: state.coupon,
    agree_terms: document.querySelector('[name="agree_terms"]').checked,
    agree_privacy: document.querySelector('[name="agree_privacy"]').checked,
    agree_optional: document.querySelector('[name="agree_optional"]').checked,
  };

  const btn = $("submit-btn");
  btn.disabled = true;
  btn.textContent = "신청 중...";
  try {
    const res = await api("/api/demo/echo", data);
    $("result").textContent =
      JSON.stringify(res.received, null, 2) + `\n\n// 서버가 계산한 총 요금: ${won(res.total)}`;
    $("result-note").innerHTML = '<span class="ok-note">✓ 신청이 접수되었어요 (예제)</span>';
    toast("신청 완료! 서버가 받은 값을 확인하세요.");
    $("result").scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (err) {
    if (err.fields) showErrors(err.fields);
    $("form-error").textContent = err.message;
    $("result-note").innerHTML = '<span class="bad-note">✗ 입력값을 확인해 주세요</span>';
  } finally {
    btn.disabled = false;
    btn.textContent = "신청하기";
  }
});
