const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char])
);

function showView(name) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach((button) => button.classList.remove("active"));
  document.getElementById(name).classList.add("active");
  document.querySelector(`[data-view="${name}"]`).classList.add("active");
}

document.querySelectorAll(".nav-btn").forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || "요청을 처리하지 못했습니다.");
  }
  return result;
}

function render(containerId, events) {
  const container = document.getElementById(containerId);
  container.innerHTML = events.length
    ? events.map((event) => {
      const location = [event.region, event.district, event.venue].filter(Boolean).join(" · ");
      const period = [event.start_date, event.end_date].filter(Boolean).join(" ~ ");
      return `<article class="card" data-id="${escapeHtml(event.id)}">
        <span class="badge">${escapeHtml(event.event_type || "미분류")}</span>
        <h3>${escapeHtml(event.title)}</h3>
        <p>${escapeHtml(location || "장소 미상")}</p>
        <p>${escapeHtml(period || "날짜 미상")}</p>
      </article>`;
    }).join("")
    : "<p>검색 결과가 없습니다.</p>";
  container.querySelectorAll(".card").forEach((node) => {
    node.addEventListener("click", () => showDetail(node.dataset.id));
  });
}

function showError(containerId, error) {
  document.getElementById(containerId).textContent = error.message;
}

function safeHomepage(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

async function showDetail(id) {
  try {
    const event = await api(`/api/events/${encodeURIComponent(id)}`);
    const fields = [
      ["유형", event.event_type || "미분류"],
      ["지역", [event.region, event.district].filter(Boolean).join(" ") || "확인 필요"],
      ["장소", event.venue || "확인 필요"],
      ["기간", [event.start_date, event.end_date].filter(Boolean).join(" ~ ") || "확인 필요"],
      ["주소", event.address || "확인 필요"],
      ["요금", event.fee || "확인 필요"],
      ["연락처", event.phone || "확인 필요"],
      ["설명", event.description || "등록된 설명이 없습니다."],
    ];
    const homepage = safeHomepage(event.homepage);
    document.getElementById("eventDetail").innerHTML =
      `<div class="detail-content"><h2>${escapeHtml(event.title)}</h2>` +
      fields.map(([label, value]) => `<p><strong>${label}:</strong> ${escapeHtml(value)}</p>`).join("") +
      (homepage ? `<p><a href="${escapeHtml(homepage)}" target="_blank" rel="noopener noreferrer">홈페이지</a></p>` : "") +
      "</div>";
    document.getElementById("eventDialog").showModal();
  } catch (error) {
    window.alert(error.message);
  }
}

async function searchEvents(params, containerId) {
  try {
    const events = await api(`/api/events?${new URLSearchParams(params)}`);
    render(containerId, events);
  } catch (error) {
    showError(containerId, error);
  }
}

document.getElementById("searchBtn").addEventListener("click", () => {
  void searchEvents({ keyword: document.getElementById("searchKeyword").value }, "searchResults");
});
document.getElementById("regionBtn").addEventListener("click", () => {
  void searchEvents({ region: document.getElementById("regionInput").value }, "regionResults");
});
document.getElementById("dateBtn").addEventListener("click", () => {
  void searchEvents({ date: document.getElementById("dateInput").value }, "dateResults");
});
document.getElementById("typeBtn").addEventListener("click", () => {
  void searchEvents({ event_type: document.getElementById("typeInput").value }, "typeResults");
});

document.querySelectorAll("[data-quick]").forEach((button) => {
  button.addEventListener("click", () => {
    const query = button.dataset.quick;
    const params = {};
    if (query.includes("서울")) params.region = "서울특별시";
    if (query.includes("축제")) params.event_type = "축제";
    if (query.includes("공연")) params.event_type = "공연";
    if (query.includes("전시")) params.event_type = "전시";
    if (query.includes("체험")) params.event_type = "체험";
    void searchEvents(params, "mainResults");
  });
});

async function askAgent(endpoint, messageId, answerId, resultsId) {
  const message = document.getElementById(messageId).value.trim();
  if (!message) {
    document.getElementById(answerId).textContent = "질문이나 원하는 조건을 입력해주세요.";
    return;
  }
  const answer = document.getElementById(answerId);
  answer.textContent = "CSV 행사 정보를 검색하고 있습니다.";
  try {
    const result = await api(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    answer.textContent = result.answer;
    render(resultsId, result.events);
  } catch (error) {
    answer.textContent = error.message;
    render(resultsId, []);
  }
}

document.getElementById("recommendBtn").addEventListener("click", () =>
  askAgent("/api/recommend", "recommendMessage", "recommendAnswer", "recommendResults")
);
document.getElementById("askBtn").addEventListener("click", () =>
  askAgent("/api/ask", "questionMessage", "questionAnswer", "questionResults")
);
document.getElementById("closeDialog").addEventListener("click", () =>
  document.getElementById("eventDialog").close()
);

async function loadStatus() {
  try {
    const status = await api("/api/status");
    document.getElementById("dataStatus").textContent = status.total
      ? `SQLite에 행사 ${status.total.toLocaleString()}건이 저장되어 있습니다.`
      : "행사 데이터가 없습니다. 데이터 준비 방법은 README.md를 확인하세요.";
    document.getElementById("typeSupport").innerHTML = status.types.map((type) =>
      `<span>${escapeHtml(type.name)}: ${type.supported ? `${type.count.toLocaleString()}건` : "데이터 없음"}</span>`
    ).join("");
    const events = await api("/api/events?limit=8");
    render("mainResults", events);
  } catch (error) {
    document.getElementById("dataStatus").textContent = error.message;
  }
}

void loadStatus();
