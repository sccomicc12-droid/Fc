// 포인트 화면: 충전 신청(무통장입금) / 포인트 결제 / 내역
const socket = connectSocket();
const STATUS_BADGE = { pending: "badge-warn", approved: "", rejected: "badge-danger" };
let minCharge = 1000;

(async () => {
  const me = await renderHeader();
  document.getElementById("depositor").value = me.nickname; // 기본값: 내 이름
  await load();
})();

async function load() {
  const d = await api("/api/points");
  minCharge = d.min_charge;
  document.getElementById("balance").textContent = d.balance.toLocaleString("ko-KR");
  document.getElementById("amount-hint").textContent = `최소 ${won(d.min_charge)}부터 충전할 수 있어요`;

  document.getElementById("products").innerHTML = d.products.map((p) => `
    <div class="product">
      <div><b>${escapeHtml(p.item)}</b><div class="muted small-text">1회 ${won(p.price)} = ${p.price.toLocaleString()}P</div></div>
      <button class="btn btn-outline btn-sm" data-slug="${escapeHtml(p.slug)}" data-name="${escapeHtml(p.item)}"
        data-price="${p.price}" ${d.balance < p.price ? "disabled" : ""}>
        ${d.balance < p.price ? "포인트 부족" : "결제하기"}</button>
    </div>`).join("") || '<p class="muted">유료 서비스가 없어요.</p>';

  document.getElementById("charge-table").innerHTML = d.charges.length ? `
    <thead><tr><th>신청 시각</th><th class="right">금액</th><th>상태</th></tr></thead>
    <tbody>${d.charges.map((c) => `
      <tr><td class="muted">${escapeHtml(c.created_at.slice(5, 16))}</td>
          <td class="right"><b>${won(c.amount)}</b></td>
          <td><span class="badge ${STATUS_BADGE[c.status]}">${escapeHtml(c.status_text)}</span></td></tr>`).join("")}</tbody>`
    : '<tr><td class="muted">아직 충전 신청이 없어요.</td></tr>';

  document.getElementById("ledger").innerHTML = d.ledger.length ? d.ledger.map((l) => `
    <li><div><b>${escapeHtml(l.reason)}</b><div class="muted small-text">${escapeHtml(l.created_at.slice(0, 16))}</div></div>
        <span class="${l.amount > 0 ? "plus" : "minus"}">${l.amount > 0 ? "+" : ""}${l.amount.toLocaleString()}P</span></li>`).join("")
    : '<li class="muted">아직 내역이 없어요.</li>';
}

// 금액 버튼을 누르면 입력칸에 채움
document.getElementById("amount-grid").addEventListener("change", (e) => {
  document.getElementById("amount").value = e.target.value;
});
document.getElementById("amount").addEventListener("input", () => {
  document.querySelectorAll('input[name="preset"]').forEach((r) => (r.checked = false));
});

// 충전 신청
document.getElementById("charge-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorBox = document.getElementById("form-error");
  const amount = Number(document.getElementById("amount").value);
  const depositor = document.getElementById("depositor").value.trim();
  if (!amount || amount < minCharge) {
    errorBox.textContent = `최소 충전 금액은 ${won(minCharge)}입니다.`;
    return;
  }
  errorBox.textContent = "";
  try {
    const { charge, bank } = await api("/api/points/charge", { amount, depositor });
    document.getElementById("bank-name").textContent = bank.bank;
    document.getElementById("bank-account").textContent = bank.account;
    document.getElementById("bank-holder").textContent = bank.holder;
    document.getElementById("bank-amount").textContent = won(charge.amount);
    document.getElementById("bank-depositor").textContent = charge.depositor;
    document.getElementById("bank-box").hidden = false;
    toast("충전 신청 완료! 안내된 계좌로 입금해 주세요.");
    load();
  } catch (err) {
    errorBox.textContent = err.message;
  }
});

document.getElementById("copy-btn").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(document.getElementById("bank-account").textContent);
    toast("계좌번호를 복사했어요.");
  } catch (_) {
    toast("복사에 실패했어요. 직접 입력해 주세요.", "error");
  }
});

// 포인트 결제
document.getElementById("products").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-slug]");
  if (!btn) return;
  if (!confirm(`${btn.dataset.name}을(를) ${Number(btn.dataset.price).toLocaleString()}P로 결제할까요?`)) return;
  try {
    const res = await api("/api/points/use", { product: btn.dataset.slug });
    toast(res.message);
    load();
  } catch (err) {
    toast(err.message, "error");
  }
});

// 상담실에서 입금 확인하면 실시간으로 알림 + 새로고침
socket.on("points_changed", (d) => {
  toast(d.approved ? `${d.amount.toLocaleString()}P가 적립되었어요!` : "충전 신청이 반려되었어요. 상담실에 문의해 주세요.",
        d.approved ? "" : "error");
  load();
});
