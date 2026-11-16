// 고객(학생) 화면: 상담 유형 선택 → 상담 요청 → 실시간 채팅
let me = null;
let room = null;      // 현재 상담방
let topic = null;     // 선택한 상담 유형 slug
const socket = connectSocket();

(async () => {
  me = await renderHeader();
  document.getElementById("greeting").textContent = `${me.nickname}님, 안녕하세요`;
  document.getElementById("empty-icon").innerHTML = icon("chat");

  // 상담 유형 목록: 학교 신청서가 있으면 맨 위에 + 일반 카테고리
  const [{ categories }, { application }] = await Promise.all([api("/api/categories"), api("/api/school/my")]);
  const items = categories.map((c) => ({ slug: c.slug, icon: c.slug, name: c.name, desc: c.description }));
  if (application) {
    items.unshift({
      slug: "school", icon: application.consult_type, name: "학교 상담 신청서",
      desc: `${application.consult_name} · ${application.anonymous ? "익명" : "실명"} 상담`,
    });
  }
  const list = document.getElementById("topic-list");
  list.innerHTML = items.map((t) => `
    <button class="side-item" data-slug="${escapeHtml(t.slug)}">
      <span class="icon">${icon(t.icon)}</span>
      <span class="meta"><b>${escapeHtml(t.name)}</b><small>${escapeHtml(t.desc)}</small></span>
    </button>`).join("");
  list.addEventListener("click", (e) => {
    const item = e.target.closest(".side-item");
    if (item) selectTopic(item.dataset.slug, item.querySelector("b").textContent);
  });

  // 진행 중인 상담이 있으면 바로 열기
  const { rooms } = await api("/api/chat/rooms");
  const open = rooms.find((r) => r.status !== "closed");
  if (open) return openRoom(open);

  const fromUrl = new URLSearchParams(location.search).get("category");
  const first = list.querySelector(`[data-slug="${CSS.escape(fromUrl || (application ? "school" : ""))}"]`);
  if (first) first.click();
})();

function selectTopic(slug, name) {
  if (room && room.status !== "closed") {
    toast("진행 중인 상담을 먼저 종료해 주세요.");
    return;
  }
  topic = slug;
  document.querySelectorAll(".side-item").forEach((el) => el.classList.toggle("active", el.dataset.slug === slug));
  document.getElementById("chat-title").textContent = name;
  document.getElementById("chat-status").textContent = "상담 시작 버튼을 눌러주세요";
  setHeadButton("start");
}

// 오른쪽 위 버튼: 상담 시작 / 상담 종료 / 새 상담
function setHeadButton(mode) {
  const btn = document.getElementById("head-btn");
  btn.disabled = false;
  btn.dataset.mode = mode;
  btn.className = mode === "close" ? "btn btn-ghost" : "btn btn-mint";
  btn.textContent = { start: "상담 시작", close: "상담 종료", new: "새 상담" }[mode];
}

document.getElementById("head-btn").addEventListener("click", async (e) => {
  const mode = e.currentTarget.dataset.mode;
  try {
    if (mode === "start") {
      const res = await api("/api/chat/rooms", { topic });
      openRoom(res.room);
    } else if (mode === "close") {
      if (confirm("상담을 종료할까요?")) await api(`/api/chat/rooms/${room.id}/close`, {});
    } else if (mode === "new") {
      location.href = "/customer";
    }
  } catch (err) {
    toast(err.message, "error");
  }
});

async function openRoom(r) {
  room = r;
  document.getElementById("topic-list").classList.add("locked");
  // 1) 이 방의 실시간 메시지를 받기 시작 → 2) 지난 메시지 불러오기 (순서가 바뀌면 메시지를 놓칠 수 있음)
  await socket.emitWithAck("join", { room_id: room.id });
  const data = await api(`/api/chat/rooms/${room.id}/messages`);
  renderMessages(data.messages, me.id);
  renderRoom(data.room);
}

function renderRoom(r) {
  room = r;
  document.getElementById("chat-title").textContent = r.topic;
  setStatus(r, r.status === "active" && r.agent_name ? ` · ${r.agent_name}` : "");
  setInputEnabled(r.status !== "closed");
  setHeadButton(r.status === "closed" ? "new" : "close");
  if (r.status === "closed") document.getElementById("topic-list").classList.remove("locked");
}

// 실시간 이벤트
socket.on("message", (msg) => { if (room && msg.room_id === room.id) appendMessage(msg, me.id); });
socket.on("room_update", (r) => { if (room && r.id === room.id) renderRoom(r); });
// 연결이 끊겼다가 다시 연결되면 상담방에 다시 들어감
socket.on("connect", () => { if (room) socket.emit("join", { room_id: room.id }); });

bindSendForm(socket, () => room && room.id);
