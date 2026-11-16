// 고객/상담원 화면이 같이 쓰는 채팅 화면 그리기 함수

const chatBody = document.getElementById("chat-body");

// 메시지 하나를 말풍선으로 추가
function appendMessage(msg, myId) {
  const el = document.createElement("div");
  const who = msg.kind === "system" ? "system" : msg.sender_id === myId ? "me" : "other";
  el.className = `bubble ${who}`;
  el.innerHTML = `${escapeHtml(msg.body)}<span class="time">${escapeHtml(msg.time)}</span>`;
  chatBody.appendChild(el);
  chatBody.scrollTop = chatBody.scrollHeight; // 맨 아래로 스크롤
}

function renderMessages(messages, myId) {
  chatBody.innerHTML = "";
  messages.forEach((m) => appendMessage(m, myId));
}

// 상단 상태 표시 (점 색깔 + 글자)
const STATUS = {
  waiting: { text: "상담원 연결 대기 중", on: false },
  active: { text: "상담 중", on: true },
  closed: { text: "상담 종료", on: false },
};
function setStatus(room, extra = "") {
  const s = STATUS[room.status];
  document.getElementById("chat-dot").classList.toggle("on", s.on);
  document.getElementById("chat-status").textContent = s.text + extra;
}

function setInputEnabled(enabled) {
  document.getElementById("chat-text").disabled = !enabled;
  document.getElementById("send-btn").disabled = !enabled;
  if (enabled) document.getElementById("chat-text").focus();
}

// 전송: 웹소켓으로 보내고 서버의 처리 결과(ack)를 기다림
function bindSendForm(socket, getRoomId) {
  document.getElementById("chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("chat-text");
    const body = input.value.trim();
    if (!body || !getRoomId()) return;
    const res = await socket.emitWithAck("send_message", { room_id: getRoomId(), body });
    if (res.error) toast(res.error, "error");
    else input.value = "";
  });
}
