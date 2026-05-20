(() => {
  // ── State ──────────────────────────────────────────────
  let uploadedFile = null;
  let allResults   = [];
  let totalRows    = 0;
  let doneCount    = 0;
  let aborted      = false;

  // ── DOM refs ────────────────────────────────────────────
  const uploadZone   = document.getElementById("upload-zone");
  const fileInput    = document.getElementById("file-input");
  const fileNameEl   = document.getElementById("file-name");
  const runBtn       = document.getElementById("run-btn");
  const progressWrap = document.getElementById("progress-bar-wrap");
  const progressFill = document.getElementById("progress-fill");
  const progressLbl  = document.getElementById("progress-label");
  const progressPct  = document.getElementById("progress-pct");
  const progressTrack = document.getElementById("progress-track");
  const resultsList  = document.getElementById("results");
  const toolbar      = document.getElementById("toolbar");
  const exportBtn    = document.getElementById("export-btn");
  const errorBanner  = document.getElementById("error-banner");

  // ── File drag & drop ────────────────────────────────────
  uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("dragover"); });
  uploadZone.addEventListener("dragleave", e => { if (!uploadZone.contains(e.relatedTarget)) uploadZone.classList.remove("dragover"); });
  uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  uploadZone.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
  });

  function setFile(f) {
    uploadedFile = f;
    fileNameEl.textContent = f.name;
    runBtn.disabled = false;
  }

  // ── Run ─────────────────────────────────────────────────
  runBtn.addEventListener("click", startLookup);

  async function startLookup() {
    if (!uploadedFile) { showError("Please select an Excel file (.xlsx)."); return; }

    hideError();
    clearResults();
    aborted  = false;
    runBtn.disabled = true;
    toolbar.style.display = "none";

    const form = new FormData();
    form.append("file", uploadedFile);

    let rows;
    try {
      const res  = await fetch("/upload", { method: "POST", body: form });
      const body = await res.json();
      if (!res.ok) { showError(body.detail || "Upload failed."); runBtn.disabled = false; return; }
      rows      = body.rows;
      totalRows = body.total;
    } catch {
      showError("Network error during upload."); runBtn.disabled = false; return;
    }

    allResults = new Array(totalRows).fill(null);
    doneCount  = 0;
    showProgress(0, totalRows);

    for (const row of rows) renderPlaceholder(row);

    for (let i = 0; i < rows.length; i++) {
      if (aborted) break;
      const row = rows[i];

      try {
        const res  = await fetch(`/fetch/${row.id}`);
        const data = await res.json();

        if (data.status === "error" && data.message?.includes("401")) {
          aborted = true;
          showError("Invalid API key (401). All requests stopped.");
          updateCard(row.id, { ...row, status: "error", message: "Invalid API key" });
          doneCount++;
          showProgress(doneCount, totalRows);
          break;
        }

        allResults[i] = data;
        updateCard(row.id, data);
      } catch {
        const err = { id: row.id, status: "error", message: "Network error", artist: row.artist, date: row.date };
        allResults[i] = err;
        updateCard(row.id, err);
      }

      doneCount++;
      showProgress(doneCount, totalRows);
      if (i < rows.length - 1) await sleep(520);
    }

    runBtn.disabled = false;
    if (!aborted) {
      toolbar.style.display = "flex";
    }
  }

  // ── Progress ─────────────────────────────────────────────
  function showProgress(done, total) {
    progressWrap.style.display = "flex";
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    progressFill.style.width = pct + "%";
    progressTrack.setAttribute("aria-valuenow", pct);
    progressLbl.textContent = `${done} / ${total} done`;
    progressPct.textContent = `${pct}%`;
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
    card.setAttribute("role", "listitem");
    card.innerHTML = `
      <div class="result-header">
        <span class="status-badge"><span class="spinner"></span></span>
        <div class="result-info">
          <div class="result-artist">${esc(row.artist)}</div>
          <div class="result-meta">${formatDate(row.date)}${row.venue ? " · " + esc(row.venue) : ""}</div>
        </div>
      </div>`;
    resultsList.appendChild(card);
  }

  function updateCard(id, data) {
    const card = document.getElementById(`card-${id}`);
    if (!card) return;

    const { status } = data;
    card.className = `result-card ${status === "found" ? "found" : status === "not_found" ? "not-found" : "error"}`;

    const icon   = status === "found" ? "✓" : status === "not_found" ? "–" : "!";
    const meta   = [formatDate(data.date), data.venue || ""].filter(Boolean).join(" · ");
    const songs  = data.songs || [];
    const songCountLabel = status === "found" ? `${songs.length} tracks` : "";

    let bodyHTML = "";
    if (status === "found") {
      bodyHTML = buildSetlistHTML(data);
    } else if (status === "not_found") {
      bodyHTML = `<p class="status-msg">No setlist found for this date.</p>`;
    } else {
      bodyHTML = `<p class="status-msg error">${esc(data.message || "Unknown error")}</p>`;
    }

    card.innerHTML = `
      <div class="result-header" onclick="toggleCard(${id})">
        <span class="status-badge">${icon}</span>
        <div class="result-info">
          <div class="result-artist">${esc(data.artist)}</div>
          <div class="result-meta">${esc(meta)}</div>
        </div>
        ${songCountLabel ? `<span class="song-count">${songCountLabel}</span>` : ""}
        <span class="expand-chevron">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </span>
      </div>
      <div class="result-body">${bodyHTML}</div>`;
  }

  function buildSetlistHTML(data) {
    const songs        = data.songs || [];
    const encoreBreaks = new Set(data.encore_breaks || []);
    let html = `<ol class="setlist">`;

    songs.forEach((song, idx) => {
      if (encoreBreaks.has(idx)) {
        html += `</ol><div class="encore-divider">Encore</div><ol class="setlist" start="${song.order}">`;
      }
      const info = song.info ? ` <span class="track-info">(${esc(song.info)})</span>` : "";
      html += `<li>
        <span class="track-num">${song.order}</span>
        <span class="track-name">${esc(song.name)}${info}</span>
      </li>`;
    });

    html += `</ol><div class="card-actions">`;

    if (data.setlist_url) {
      html += `<a class="action-link" href="${esc(data.setlist_url)}" target="_blank" rel="noopener noreferrer">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        setlist.fm
      </a>`;
    }

    html += `<a class="action-link pdf-btn" href="/pdf/${data.id}" download>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      Download PDF
    </a>`;

    html += `</div>`;
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
    window.location.href = `/export?results=${encodeURIComponent(JSON.stringify(payload))}`;
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

  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  function formatDate(ddMMYYYY) {
    if (!ddMMYYYY) return "";
    const [dd, mm, yyyy] = ddMMYYYY.split("-");
    if (!dd || !mm || !yyyy) return ddMMYYYY;
    return `${parseInt(dd, 10)} ${MONTHS[parseInt(mm, 10) - 1] ?? mm} ${yyyy}`;
  }
})();
