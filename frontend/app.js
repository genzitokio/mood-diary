const API = "";

const form = document.getElementById("entry-form");
const textInput = document.getElementById("text");
const emojiInput = document.getElementById("emoji");
const submitBtn = document.getElementById("submit-btn");
const formStatus = document.getElementById("form-status");
const entriesList = document.getElementById("entries");
const chartCanvas = document.getElementById("chart");
const pieCanvas = document.getElementById("pie");
const weekdayCanvas = document.getElementById("weekday-chart");
const summaryEl = document.getElementById("summary");

let chart = null;
let pie = null;
let weekdayChart = null;

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

function renderPie(summary) {
  const data = [
    summary.by_label.positive,
    summary.by_label.neutral,
    summary.by_label.negative,
  ];
  if (pie) pie.destroy();
  pie = new Chart(pieCanvas, {
    type: "doughnut",
    data: {
      labels: ["positive", "neutral", "negative"],
      datasets: [{
        data,
        backgroundColor: ["#4ade80", "#94a3b8", "#f87171"],
        borderColor: "#181b22",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#e6e8ef" } } },
    },
  });
}

function renderSummary(summary) {
  const mood = summary.avg_score;
  const moodTxt = mood === 0
    ? "0.00"
    : `${mood >= 0 ? "+" : ""}${mood.toFixed(2)}`;
  const period = summary.first_day && summary.last_day
    ? (summary.first_day === summary.last_day
        ? summary.first_day
        : `${summary.first_day} → ${summary.last_day}`)
    : "—";
  summaryEl.innerHTML = `
    <div class="tile"><div class="k">всего записей</div><div class="v">${summary.total}</div></div>
    <div class="tile"><div class="k">средний score</div><div class="v">${moodTxt}</div></div>
    <div class="tile pos"><div class="k">positive</div><div class="v">${summary.by_label.positive}</div></div>
    <div class="tile neu"><div class="k">neutral</div><div class="v">${summary.by_label.neutral}</div></div>
    <div class="tile neg"><div class="k">negative</div><div class="v">${summary.by_label.negative}</div></div>
    <div class="tile"><div class="k">период</div><div class="v" style="font-size:13px">${period}</div></div>
  `;
}

function renderWeekday(weekday) {
  const labels = weekday.map((w) => w.weekday);
  const scores = weekday.map((w) => w.avg_score);
  const colors = scores.map((s) =>
    s > 0.1 ? "#4ade80" : s < -0.1 ? "#f87171" : "#94a3b8"
  );

  if (weekdayChart) weekdayChart.destroy();
  weekdayChart = new Chart(weekdayCanvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "средний score",
        data: scores,
        backgroundColor: colors,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      scales: {
        y: { suggestedMin: -1, suggestedMax: 1, ticks: { color: "#8b91a3" } },
        x: { ticks: { color: "#8b91a3" } },
      },
      plugins: { legend: { display: false } },
    },
  });
}

async function refresh() {
  try {
    const [entries, daily, summary, weekday] = await Promise.all([
      api("/entries"),
      api("/analytics/daily"),
      api("/analytics/summary"),
      api("/analytics/weekday"),
    ]);
    renderEntries(entries);
    renderChart(daily);
    renderSummary(summary);
    renderPie(summary);
    renderWeekday(weekday);
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
    const head = `сохранено: ${created.sentiment_label} (${created.sentiment_score.toFixed(2)})`;
    setStatus(created.recommendation ? `${head} — ${created.recommendation}` : head);
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
