// 상담원 화면: 대기 학생 수락 → 실시간 상담 / 포인트 입금 확인
let me = null;
let current = null;          // 지금 보고 있는 상담방
const unread = new Set();    // 새 메시지가 온 방 번호
let lastWaiting = null;   // 처음 불러올 때는 알림을 띄우지 않기 위해 null
const socket = connectSocket();

(async () => {
  me = await renderHeader();
  document.getElementById("empty-icon").innerHTML = icon("inbox");
  document.querySelectorAll(".stat .label").forEach((el) => el.insertAdjacentHTML("afterbegin", icon(el.dataset.icon)));
  await Promise.all([loadSummary(), loadRooms(), loadCharges()]);
})();

// ----- 상단 숫자 -----
async function loadSummary() {
  const s = await api("/api/chat/summary");
  document.getElementById("s-waiting").textContent = s.waiting;
  document.getElementById("s-active").textContent = s.active;
  document.getElementById("s-closed").textContent = s.closed_today;
  document.getElementById("s-charges").textContent = s.pending_charges;
  if (lastWaiting !== null && s.waiting > lastWaiting) toast("새 상담 요청이 들어왔어요!");
  lastWaiting = s.waiting;
}

// ----- 상담 목록 -----
async function loadRooms() {
  const { rooms } = await api("/api/chat/rooms");
  const list = document.getElementById("room-list");
  if (!rooms.length) {
    list.innerHTML = '<div class="empty"><b>대기 중인 상담이 없어요</b><p>학생이 상담을 요청하면 여기에 나타납니다.</p></div>';
    return;
  }
  list.innerHTML = rooms.map((r) => `
    <button class="side-item ${current && current.id === r.id ? "active" : ""}" data-id="${r.id}">
      <span class="icon">${icon(r.anonymous ? "account" : "chat")}</span>
      <span class="meta">
        <b>${escapeHtml(r.customer_name)} <span class="badge ${r.status === "waiting" ? "badge-warn" : ""}">${r.status === "waiting" ? "대기" : "상담 중"}</span></b>
        <small>${escapeHtml(r.topic)}</small>
        <small class="preview">${escapeHtml(r.last_message || "")}</small>
      </span>
      ${unread.has(r.id) ? '<span class="unread"></span>' : ""}
    </button>`).join("");
}

document.getElementById("room-list").addEventListener("click", (e) => {
  const item = e.target.closest(".side-item");
  if (item) openRoom(Number(item.dataset.id));
});

async function openRoom(id) {
  unread.delete(id);
  await socket.emitWithAck("join", { room_id: id });
  const data = await api(`/api/chat/rooms/${id}/messages`);
  renderMessages(data.messages, me.id);
  renderRoom(data.room);
  loadRooms();
}

function renderRoom(r) {
  current = r;
  document.getElementById("chat-title").textContent = `${r.customer_name} · ${r.topic}`;
  setStatus(r);
  const mine = r.status === "active" && r.agent_id === me.id;
  setInputEnabled(mine);
  const btn = document.getElementById("head-btn");
  btn.hidden = r.status === "closed";
  btn.dataset.mode = r.status === "waiting" ? "accept" : "close";
  btn.className = r.status === "waiting" ? "btn btn-mint" : "btn btn-ghost";
  btn.textContent = r.status === "waiting" ? "상담 수락" : "상담 종료";
}

document.getElementById("head-btn").addEventListener("click", async (e) => {
  if (!current) return;
  const mode = e.currentTarget.dataset.mode;
  if (mode === "close" && !confirm("상담을 종료할까요?")) return;
  try {
    await api(`/api/chat/rooms/${current.id}/${mode}`, {});
  } catch (err) {
    toast(err.message, "error");
  }
});

// ----- 포인트 입금 확인 -----
const STATUS_BADGE = { pending: "badge-warn", approved: "", rejected: "badge-danger" };

async function loadCharges() {
  const { charges } = await api("/api/admin/charges");
  const table = document.getElementById("charge-table");
  if (!charges.length) {
    table.innerHTML = '<tr><td class="muted center" colspan="6">충전 신청이 없어요.</td></tr>';
    return;
  }
  table.innerHTML = `
    <thead><tr><th>신청 시각</th><th>학생</th><th>입금자명</th><th class="right">금액</th><th>상태</th><th></th></tr></thead>
    <tbody>${charges.map((c) => `
      <tr>
        <td class="muted">${escapeHtml(c.created_at.slice(5, 16))}</td>
        <td>${escapeHtml(c.real_name || c.nickname)} <span class="muted">(${escapeHtml(c.username)})</span></td>
        <td>${escapeHtml(c.depositor)}</td>
        <td class="right"><b>${won(c.amount)}</b></td>
        <td><span class="badge ${STATUS_BADGE[c.status]}">${escapeHtml(c.status_text)}</span></td>
        <td class="right">${c.status === "pending" ? `
          <button class="btn btn-mint btn-sm" data-act="approve" data-id="${c.id}">입금 확인</button>
          <button class="btn btn-ghost btn-sm" data-act="reject" data-id="${c.id}">반려</button>` : ""}</td>
      </tr>`).join("")}</tbody>`;
}

document.getElementById("charge-table").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-act]");
  if (!btn) return;
  const approve = btn.dataset.act === "approve";
  const row = btn.closest("tr").children;
  const msg = approve
    ? `${row[2].textContent}님의 ${row[3].textContent} 입금을 확인했나요?\n확인하면 포인트가 바로 적립됩니다.`
    : "이 충전 신청을 반려할까요?";
  if (!confirm(msg)) return;
  try {
    await api(`/api/admin/charges/${btn.dataset.id}/${btn.dataset.act}`, {});
    toast(approve ? "포인트가 적립되었습니다." : "반려되었습니다.");
  } catch (err) {
    toast(err.message, "error");
  }
});

// ----- 실시간 이벤트 -----
socket.on("message", (msg) => { if (current && msg.room_id === current.id) appendMessage(msg, me.id); });
socket.on("room_update", (r) => { if (current && r.id === current.id) renderRoom(r); });
socket.on("rooms_changed", ({ room_id }) => {
  if (!current || room_id !== current.id) unread.add(room_id);
  loadRooms();
  loadSummary();
});
socket.on("charges_changed", () => { loadCharges(); loadSummary(); });
socket.on("connect", () => { if (current) socket.emit("join", { room_id: current.id }); });

bindSendForm(socket, () => current && current.id);
