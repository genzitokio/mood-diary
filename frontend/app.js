const API = "";

const form = document.getElementById("entry-form");
const textInput = document.getElementById("text");
const emojiInput = document.getElementById("emoji");
const submitBtn = document.getElementById("submit-btn");
const formStatus = document.getElementById("form-status");
const entriesList = document.getElementById("entries");
const chartCanvas = document.getElementById("chart");

let chart = null;

function setStatus(msg, isError = false) {
  formStatus.textContent = msg;
  formStatus.classList.toggle("error", isError);
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "content-type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function renderEntries(entries) {
  entriesList.innerHTML = "";
  if (entries.length === 0) {
    entriesList.innerHTML = '<li class="muted">Пока пусто. Добавь первую запись.</li>';
    return;
  }
  for (const e of entries) {
    const li = document.createElement("li");
    const label = e.sentiment_label || "neutral";
    li.className = `entry ${label}`;
    const scoreTxt = e.sentiment_score == null ? "" :
      `score ${e.sentiment_score >= 0 ? "+" : ""}${e.sentiment_score.toFixed(2)}`;
    li.innerHTML = `
      <span class="emoji">${escapeHtml(e.emoji || "")}</span>
      <div class="body">
        <div class="text">${escapeHtml(e.text)}</div>
        <div class="meta">
          <span class="badge ${label}">${label}</span>
          <span>${scoreTxt}</span>
          <span>${fmtDate(e.created_at)}</span>
        </div>
      </div>
      <button class="del" data-id="${e.id}" title="удалить">✕</button>
    `;
    entriesList.appendChild(li);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function renderChart(daily) {
  const labels = daily.map((d) => d.day);
  const scores = daily.map((d) => d.avg_score);
  const counts = daily.map((d) => d.count);

  if (chart) chart.destroy();
  chart = new Chart(chartCanvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "среднее настроение",
          data: scores,
          borderColor: "#6366f1",
          backgroundColor: "rgba(99,102,241,0.15)",
          tension: 0.25,
          fill: true,
          yAxisID: "y",
        },
        {
          label: "записей за день",
          data: counts,
          borderColor: "#94a3b8",
          borderDash: [4, 4],
          tension: 0,
          fill: false,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y:  { suggestedMin: -1, suggestedMax: 1, title: { display: true, text: "score [-1..1]" } },
        y1: { position: "right", beginAtZero: true, grid: { drawOnChartArea: false }, title: { display: true, text: "count" } },
      },
      plugins: {
        legend: { labels: { color: "#e6e8ef" } },
      },
    },
  });
}

async function refresh() {
  try {
    const [entries, daily] = await Promise.all([
      api("/entries"),
      api("/analytics/daily"),
    ]);
    renderEntries(entries);
    renderChart(daily);
  } catch (e) {
    setStatus(`ошибка загрузки: ${e.message}`, true);
  }
}

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const text = textInput.value.trim();
  if (!text) return;
  submitBtn.disabled = true;
  setStatus("анализ...");
  try {
    const created = await api("/entries", {
      method: "POST",
      body: JSON.stringify({ text, emoji: emojiInput.value || null }),
    });
    setStatus(`сохранено: ${created.sentiment_label} (${created.sentiment_score.toFixed(2)})`);
    textInput.value = "";
    emojiInput.value = "";
    await refresh();
  } catch (e) {
    setStatus(`ошибка: ${e.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});

entriesList.addEventListener("click", async (ev) => {
  const btn = ev.target.closest("button.del");
  if (!btn) return;
  const id = btn.dataset.id;
  btn.disabled = true;
  try {
    await api(`/entries/${id}`, { method: "DELETE" });
    await refresh();
  } catch (e) {
    setStatus(`не удалось удалить: ${e.message}`, true);
    btn.disabled = false;
  }
});

refresh();
