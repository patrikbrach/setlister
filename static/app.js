(() => {
  // ── State ──────────────────────────────────────────────
  let uploadedFile = null;
  let allResults = [];
  let totalRows = 0;
  let doneCount = 0;
  let aborted = false;
  let apiBaked = false;

  // ── DOM refs ────────────────────────────────────────────
  const apiKeyInput  = document.getElementById("api-key");
  const apiKeyWrap   = document.querySelector(".api-key-wrap");
  const uploadZone   = document.getElementById("upload-zone");
  const fileInput    = document.getElementById("file-input");
  const fileNameEl   = document.getElementById("file-name");
  const runBtn       = document.getElementById("run-btn");
  const progressWrap = document.getElementById("progress-bar-wrap");
  const progressFill = document.getElementById("progress-fill");
  const progressLbl  = document.getElementById("progress-label");
  const resultsList  = document.getElementById("results");
  const exportBtn    = document.getElementById("export-btn");
  const errorBanner  = document.getElementById("error-banner");

  // ── Init: check if API key is pre-configured on server ──
  fetch("/config")
    .then(r => r.json())
    .then(cfg => {
      apiBaked = cfg.api_key_baked;
      if (apiBaked) {
        apiKeyWrap.style.display = "none";
      }
    })
    .catch(() => {}); // ignore if /config fails

  // ── File drag & drop ────────────────────────────────────
  uploadZone.addEventListener("click", () => fileInput.click());
  uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
  uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  function setFile(f) {
    uploadedFile = f;
    fileNameEl.textContent = f.name;
  }

  // ── Run ─────────────────────────────────────────────────
  runBtn.addEventListener("click", startLookup);

  async function startLookup() {
    const apiKey = apiBaked ? "" : apiKeyInput.value.trim();
    if (!apiBaked && !apiKey) { showError("Ange en API-nyckel."); return; }
    if (!uploadedFile) { showError("Välj en Excel-fil (.xlsx)."); return; }

    hideError();
    clearResults();
    aborted = false;
    runBtn.disabled = true;
    exportBtn.style.display = "none";

    // 1. Upload file
    const form = new FormData();
    form.append("file", uploadedFile);
    form.append("api_key", apiKey);

    let rows;
    try {
      const res = await fetch("/upload", { method: "POST", body: form });
      const body = await res.json();
      if (!res.ok) { showError(body.detail || "Uppladdning misslyckades."); runBtn.disabled = false; return; }
      rows = body.rows;
      totalRows = body.total;
    } catch (e) {
      showError("Nätverksfel vid uppladdning."); runBtn.disabled = false; return;
    }

    // 2. Create placeholder cards
    allResults = new Array(totalRows).fill(null);
    doneCount = 0;
    showProgress(0, totalRows);

    for (const row of rows) {
      renderPlaceholder(row);
    }

    // 3. Fetch each row sequentially (with 0.5 s delay between)
    for (let i = 0; i < rows.length; i++) {
      if (aborted) break;
      const row = rows[i];
      try {
        const res = await fetch(`/fetch/${row.id}?api_key=${encodeURIComponent(apiKey)}`);
        const data = await res.json();

        if (data.status === "error" && data.message && data.message.includes("401")) {
          aborted = true;
          showError("Ogiltig API-nyckel (401). Alla anrop stoppade.");
          updateCard(row.id, { ...row, status: "error", message: "Ogiltig API-nyckel" });
          doneCount++;
          showProgress(doneCount, totalRows);
          break;
        }

        allResults[i] = data;
        updateCard(row.id, data);
      } catch (e) {
        const errResult = { id: row.id, status: "error", message: "Nätverksfel", artist: row.artist, date: row.date };
        allResults[i] = errResult;
        updateCard(row.id, errResult);
      }

      doneCount++;
      showProgress(doneCount, totalRows);

      if (i < rows.length - 1) {
        await sleep(500);
      }
    }

    runBtn.disabled = false;
    if (!aborted) {
      exportBtn.style.display = "flex";
    }
  }

  // ── Progress ─────────────────────────────────────────────
  function showProgress(done, total) {
    progressWrap.style.display = "flex";
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    progressFill.style.width = pct + "%";
    progressLbl.textContent = `${done} / ${total} klara`;
  }

  // ── Card rendering ───────────────────────────────────────
  function clearResults() {
    resultsList.innerHTML = "";
    progressWrap.style.display = "none";
    progressFill.style.width = "0%";
  }

  function renderPlaceholder(row) {
    const card = document.createElement("div");
    card.className = "result-card";
    card.id = `card-${row.id}`;
    card.innerHTML = `
      <div class="result-header">
        <span class="status-icon"><span class="spinner"></span></span>
        <span class="result-title">${esc(row.artist)} <span class="meta">– ${formatDate(row.date)}${row.venue ? " – " + esc(row.venue) : ""}</span></span>
      </div>`;
    resultsList.appendChild(card);
  }

  function updateCard(id, data) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return;

    const { status } = data;
    card.className = `result-card ${status === "found" ? "found" : status === "not_found" ? "not-found" : "error"}`;

    const icon = status === "found" ? "✅" : status === "not_found" ? "❌" : "⚠️";
    const venueDisplay = data.venue || "";
    const subInfo = [formatDate(data.date), venueDisplay].filter(Boolean).join(" – ");

    let bodyHTML = "";
    if (status === "found") {
      bodyHTML = buildSetlistHTML(data);
    } else if (status === "not_found") {
      bodyHTML = `<p class="status-msg">Ingen setlist hittades för detta datum.</p>`;
    } else {
      bodyHTML = `<p class="status-msg" style="color:var(--red)">${esc(data.message || "Okänt fel")}</p>`;
    }

    card.innerHTML = `
      <div class="result-header" onclick="toggleCard(${id})">
        <span class="status-icon">${icon}</span>
        <span class="result-title">${esc(data.artist)} <span class="meta">– ${esc(subInfo)}</span></span>
        <span class="expand-icon">▼</span>
      </div>
      <div class="result-body">${bodyHTML}</div>`;
  }

  function buildSetlistHTML(data) {
    const songs = data.songs || [];
    const encoreBreaks = new Set(data.encore_breaks || []);
    let html = `<ol class="setlist">`;

    songs.forEach((song, idx) => {
      if (encoreBreaks.has(idx)) {
        html += `</ol><div class="encore-divider">Encore</div><ol class="setlist" start="${song.order}">`;
      }
      const info = song.info ? ` <span class="info">(${esc(song.info)})</span>` : "";
      html += `<li><span class="num">${song.order}.</span><span>${esc(song.name)}${info}</span></li>`;
    });

    html += `</ol>`;

    if (data.setlist_url) {
      html += `<a class="setlist-link" href="${esc(data.setlist_url)}" target="_blank" rel="noopener">
        ↗ Öppna på setlist.fm
      </a>`;
    }

    return html;
  }

  // ── Toggle card ──────────────────────────────────────────
  window.toggleCard = function(id) {
    const card = document.getElementById(`card-${id}`);
    if (card) card.classList.toggle("open");
  };

  // ── Export ───────────────────────────────────────────────
  exportBtn.addEventListener("click", () => {
    const payload = allResults.filter(Boolean);
    const encoded = encodeURIComponent(JSON.stringify(payload));
    window.location.href = `/export?results=${encoded}`;
  });

  // ── Error banner ─────────────────────────────────────────
  function showError(msg) {
    errorBanner.textContent = msg;
    errorBanner.style.display = "block";
  }
  function hideError() {
    errorBanner.style.display = "none";
  }

  // ── Helpers ──────────────────────────────────────────────
  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  function esc(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const MONTHS_SV = ["jan","feb","mar","apr","maj","jun","jul","aug","sep","okt","nov","dec"];
  function formatDate(ddMMYYYY) {
    if (!ddMMYYYY) return "";
    const [dd, mm, yyyy] = ddMMYYYY.split("-");
    if (!dd || !mm || !yyyy) return ddMMYYYY;
    const monthIdx = parseInt(mm, 10) - 1;
    return `${parseInt(dd, 10)} ${MONTHS_SV[monthIdx] ?? mm} ${yyyy}`;
  }
})();
