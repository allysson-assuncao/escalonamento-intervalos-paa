/* Motor interativo do simulador passo a passo e comparativo dos 4 algoritmos (SVG sem dependências) */

const SVG_NS = "http://www.w3.org/2000/svg";

const PHASE_LABELS = {
  PREPROCESSING: "Pré-processamento",
  SORTING: "Ordenação",
  PREDECESSORS: "Predecessores p[i]",
  SELECTION_OR_DP: "Seleção / DP",
  BACKTRACKING: "Backtracking",
  RESULT: "Resultado",
};

const appState = {
  presets: [],
  surgeries: [],
  shiftConfig: { closing_horizon: 1080, shift_window: null },
  trace: null,
  currentStepIndex: 0,
  autoPlayTimer: null,
};

function formatMinutes(minutes) {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

function normalizeHhmmDigits(digits) {
  if (!digits) return "";
  if (digits.length === 1) return `0${digits}:00`;
  if (digits.length === 2) return `${digits}:00`;
  if (digits.length === 3) return `0${digits[0]}:${digits.slice(1)}`;
  return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
}

function attachHhmmInputMask(inputEl) {
  inputEl.addEventListener("input", () => {
    const digits = inputEl.value.replace(/\D/g, "").slice(0, 4);
    inputEl.value = digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits;
  });

  inputEl.addEventListener("blur", () => {
    const digits = inputEl.value.replace(/\D/g, "").slice(0, 4);
    if (digits.length > 0) {
      inputEl.value = normalizeHhmmDigits(digits);
    }
  });
}

function parseHhmmToMinutes(rawValue, fieldLabel) {
  const trimmed = String(rawValue || "").trim();
  const match = /^(\d{1,2}):(\d{2})$/.exec(trimmed);
  if (!match) {
    throw new Error(`${fieldLabel} deve estar no formato HH:MM (ex: 12:30).`);
  }
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (minutes > 59 || hours > 24 || (hours === 24 && minutes > 0)) {
    throw new Error(`${fieldLabel} possui horário inválido (${trimmed}). Use entre 00:00 e 24:00.`);
  }
  return hours * 60 + minutes;
}

function createSvgElement(tag, attrs = {}) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, String(value));
  }
  return el;
}

function showError(message) {
  const banner = document.getElementById("global-error-banner");
  if (!message) {
    banner.textContent = "";
    banner.classList.add("hidden");
    return;
  }
  banner.textContent = message;
  banner.classList.remove("hidden");
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Erro HTTP ${response.status}`);
  }
  return data;
}

function readShiftConfigFromDom() {
  const shiftEnabled = document.getElementById("shift-enabled-checkbox").checked;
  if (!shiftEnabled) {
    return null;
  }
  const horizon = parseHhmmToMinutes(
    document.getElementById("horizon-input").value,
    "Horizonte H"
  );
  if (horizon <= 0) {
    throw new Error("O horizonte H deve ser maior que 00:00.");
  }
  const windowEnabled = document.getElementById("window-enabled-checkbox").checked;
  let shiftWindow = null;
  if (windowEnabled) {
    const winStart = parseHhmmToMinutes(
      document.getElementById("window-start-input").value,
      "Início A da janela"
    );
    const winEnd = parseHhmmToMinutes(
      document.getElementById("window-end-input").value,
      "Fim B da janela"
    );
    if (winStart >= winEnd) {
      throw new Error("Na janela [A, B], o início A deve ser menor que o fim B.");
    }
    if (winEnd > horizon) {
      throw new Error("O fim B da janela [A, B] não pode ultrapassar o horizonte H.");
    }
    shiftWindow = { start: winStart, end: winEnd };
  }
  return {
    closing_horizon: horizon,
    shift_window: shiftWindow,
  };
}

function syncShiftConfigToDom(shiftConfig) {
  const shiftCheckbox = document.getElementById("shift-enabled-checkbox");
  const shiftFields = document.getElementById("shift-fields");
  const windowCheckbox = document.getElementById("window-enabled-checkbox");
  const windowFields = document.getElementById("window-fields");
  const horizonInput = document.getElementById("horizon-input");
  const horizonHhmm = document.getElementById("horizon-hhmm");

  if (!shiftConfig) {
    shiftCheckbox.checked = false;
    shiftFields.classList.add("hidden");
    windowCheckbox.checked = false;
    windowFields.classList.add("hidden");
    return;
  }

  shiftCheckbox.checked = true;
  shiftFields.classList.remove("hidden");
  horizonInput.value = formatMinutes(shiftConfig.closing_horizon);
  horizonHhmm.textContent = `${shiftConfig.closing_horizon} min`;

  if (shiftConfig.shift_window) {
    windowCheckbox.checked = true;
    windowFields.classList.remove("hidden");
    document.getElementById("window-start-input").value = formatMinutes(shiftConfig.shift_window.start);
    document.getElementById("window-end-input").value = formatMinutes(shiftConfig.shift_window.end);
  } else {
    windowCheckbox.checked = false;
    windowFields.classList.add("hidden");
  }
}

function renderSurgeriesEditorTable() {
  const tbody = document.getElementById("surgeries-editor-tbody");
  tbody.replaceChildren();
  document.getElementById("surgery-count-badge").textContent = String(appState.surgeries.length);

  appState.surgeries.forEach((surgery, idx) => {
    const tr = document.createElement("tr");

    const tdId = document.createElement("td");
    tdId.textContent = surgery.surgery_id;

    const tdTime = document.createElement("td");
    tdTime.textContent = `${formatMinutes(surgery.start_time)}–${formatMinutes(surgery.finish_time)}`;

    const tdType = document.createElement("td");
    tdType.textContent =
      surgery.surgery_type === "CONTAMINATED"
        ? `CONTAM (+${surgery.sterilization_duration}m)`
        : "CLEAN";

    const tdAct = document.createElement("td");
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn-danger-sm";
    delBtn.textContent = "×";
    delBtn.title = "Remover cirurgia";
    delBtn.addEventListener("click", () => {
      appState.surgeries.splice(idx, 1);
      renderSurgeriesEditorTable();
      runActiveTabSimulation();
    });
    tdAct.appendChild(delBtn);

    tr.append(tdId, tdTime, tdType, tdAct);
    tbody.appendChild(tr);
  });
}

function loadPresetById(scenarioId) {
  const preset = appState.presets.find((p) => p.scenario_id === scenarioId);
  if (!preset) {
    return;
  }
  appState.surgeries = preset.surgeries.map((item) => ({ ...item }));
  appState.shiftConfig = preset.shift_config
    ? JSON.parse(JSON.stringify(preset.shift_config))
    : null;
  document.getElementById("preset-description").textContent = preset.description;
  syncShiftConfigToDom(appState.shiftConfig);
  renderSurgeriesEditorTable();
}

function computeGanttDomain(items, shiftConfig) {
  let minT = Infinity;
  let maxT = -Infinity;
  for (const item of items) {
    minT = Math.min(minT, item.start_time);
    const sterilEnd = item.finish_time + (item.sterilization_duration || 0);
    const rel =
      typeof item.effective_release_time === "number"
        ? item.effective_release_time
        : sterilEnd;
    maxT = Math.max(maxT, sterilEnd, rel);
  }
  if (shiftConfig) {
    maxT = Math.max(maxT, shiftConfig.closing_horizon);
    if (shiftConfig.shift_window) {
      minT = Math.min(minT, shiftConfig.shift_window.start);
      maxT = Math.max(maxT, shiftConfig.shift_window.end);
    }
  }
  if (!Number.isFinite(minT)) {
    minT = 480;
    maxT = 1080;
  }
  return { minT, maxT };
}

function buildGanttSvg(
  items,
  shiftConfig,
  statuses = {},
  activeId = null,
  lastRelease = null,
  sharedDomain = null
) {
  const width = 900;
  const margin = { top: 28, right: 30, bottom: 26, left: 110 };
  const rowHeight = 28;
  const height = Math.max(120, margin.top + margin.bottom + Math.max(1, items.length) * rowHeight);

  const domain = sharedDomain || computeGanttDomain(items, shiftConfig);
  const pad = Math.max(30, Math.round((domain.maxT - domain.minT) * 0.08));
  const domainStart = Math.max(0, domain.minT - pad);
  const domainEnd = domain.maxT + pad;
  const plotWidth = width - margin.left - margin.right;

  const scaleX = (t) => margin.left + ((t - domainStart) / Math.max(1, domainEnd - domainStart)) * plotWidth;

  const svg = createSvgElement("svg", {
    viewBox: `0 0 ${width} ${height}`,
    width: "100%",
    style: "max-height: 430px; display: block; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;",
  });

  const defs = createSvgElement("defs");
  const pattern = createSvgElement("pattern", {
    id: "steril-hatch",
    width: "8",
    height: "8",
    patternUnits: "userSpaceOnUse",
    patternTransform: "rotate(45)",
  });
  pattern.appendChild(createSvgElement("rect", { width: "8", height: "8", fill: "#fef3c7" }));
  pattern.appendChild(createSvgElement("line", { x1: "0", y1: "0", x2: "0", y2: "8", stroke: "#d97706", "stroke-width": "3" }));
  defs.appendChild(pattern);
  svg.appendChild(defs);

  // Grade horária
  const tickCount = 7;
  for (let i = 0; i <= tickCount; i += 1) {
    const tVal = Math.round(domainStart + ((domainEnd - domainStart) * i) / tickCount);
    const x = scaleX(tVal);
    svg.appendChild(createSvgElement("line", {
      x1: x,
      y1: margin.top,
      x2: x,
      y2: height - margin.bottom,
      stroke: "#e2e8f0",
      "stroke-width": "1",
    }));
    const label = createSvgElement("text", {
      x,
      y: height - 8,
      "text-anchor": "middle",
      "font-size": "11",
      fill: "#64748b",
    });
    label.textContent = formatMinutes(tVal);
    svg.appendChild(label);
  }

  // Janela de troca [A, B]
  if (shiftConfig && shiftConfig.shift_window) {
    const xA = scaleX(shiftConfig.shift_window.start);
    const xB = scaleX(shiftConfig.shift_window.end);
    svg.appendChild(createSvgElement("rect", {
      x: xA,
      y: margin.top,
      width: Math.max(2, xB - xA),
      height: height - margin.top - margin.bottom,
      fill: "rgba(239, 68, 68, 0.12)",
      stroke: "#ef4444",
      "stroke-dasharray": "4,3",
    }));
    const winTxt = createSvgElement("text", {
      x: (xA + xB) / 2,
      y: margin.top - 8,
      "text-anchor": "middle",
      "font-size": "11",
      "font-weight": "700",
      fill: "#b91c1c",
    });
    winTxt.textContent = `Plantão [${formatMinutes(shiftConfig.shift_window.start)}, ${formatMinutes(shiftConfig.shift_window.end)}]`;
    svg.appendChild(winTxt);
  }

  // Horizonte H
  if (shiftConfig) {
    const xH = scaleX(shiftConfig.closing_horizon);
    svg.appendChild(createSvgElement("line", {
      x1: xH,
      y1: margin.top,
      x2: xH,
      y2: height - margin.bottom,
      stroke: "#0f172a",
      "stroke-width": "2",
      "stroke-dasharray": "6,4",
    }));
    const hTxt = createSvgElement("text", {
      x: xH,
      y: margin.top - 8,
      "text-anchor": "middle",
      "font-size": "11",
      "font-weight": "700",
      fill: "#0f172a",
    });
    hTxt.textContent = `H=${formatMinutes(shiftConfig.closing_horizon)}`;
    svg.appendChild(hTxt);
  }

  // Linha de corte last_release
  if (typeof lastRelease === "number" && lastRelease >= 0) {
    const xR = scaleX(lastRelease);
    svg.appendChild(createSvgElement("line", {
      x1: xR,
      y1: margin.top,
      x2: xR,
      y2: height - margin.bottom,
      stroke: "#16a34a",
      "stroke-width": "2.2",
    }));
  }

  items.forEach((item, rowIdx) => {
    const y = margin.top + rowIdx * rowHeight + 4;
    const barH = rowHeight - 9;
    const status = statuses[item.surgery_id] || "PENDING";
    const isActive = item.surgery_id === activeId;

    const idLabel = createSvgElement("text", {
      x: margin.left - 8,
      y: y + barH * 0.72,
      "text-anchor": "end",
      "font-size": "12",
      "font-weight": isActive ? "800" : "600",
      fill: status === "DISCARDED_INFEASIBLE" ? "#94a3b8" : "#1e293b",
    });
    idLabel.textContent = item.surgery_id;
    svg.appendChild(idLabel);

    const xStart = scaleX(item.start_time);
    const xFinish = scaleX(item.finish_time);
    const xSterilEnd = scaleX(item.finish_time + item.sterilization_duration);
    const xRelease = scaleX(item.effective_release_time);

    let fill = item.surgery_type === "CONTAMINATED" ? "#d97706" : "#0284c7";
    let opacity = "0.85";
    let stroke = "#0f172a";
    let strokeW = "0.8";

    if (status === "SELECTED") {
      fill = "#15803d";
      opacity = "0.95";
      stroke = "#052e16";
      strokeW = "2";
    } else if (status === "DISCARDED_INFEASIBLE") {
      fill = "#94a3b8";
      opacity = "0.4";
      stroke = "#64748b";
    } else if (status === "REJECTED_CONFLICT") {
      fill = "#ef4444";
      opacity = "0.45";
      stroke = "#991b1b";
    }

    if (isActive) {
      stroke = "#eab308";
      strokeW = "3";
    }

    if (item.sterilization_duration > 0) {
      svg.appendChild(createSvgElement("rect", {
        x: xFinish,
        y,
        width: Math.max(2, xSterilEnd - xFinish),
        height: barH,
        fill: "url(#steril-hatch)",
        stroke: "#d97706",
        "stroke-width": "1",
        opacity: status === "DISCARDED_INFEASIBLE" ? "0.35" : "0.95",
      }));
    }

    svg.appendChild(createSvgElement("rect", {
      x: xStart,
      y,
      width: Math.max(3, xFinish - xStart),
      height: barH,
      rx: "3",
      fill,
      opacity,
      stroke,
      "stroke-width": strokeW,
    }));

    // Marcador de liberação efetiva r_i
    svg.appendChild(createSvgElement("line", {
      x1: xRelease,
      y1: y - 2,
      x2: xRelease,
      y2: y + barH + 2,
      stroke: "#1d4ed8",
      "stroke-width": "2",
    }));
  });

  return svg;
}

function renderComplexitySummary(summary) {
  if (!summary) return;
  document.getElementById("summary-time-badge").textContent = `Tempo: ${summary.time_complexity}`;
  document.getElementById("summary-space-badge").textContent = `Espaço: ${summary.space_complexity}`;
  document.getElementById("summary-sizes-badge").textContent =
    `n=${summary.input_n} | viáveis=${summary.feasible_n}`;
  document.getElementById("summary-sorting-formula").textContent = summary.sorting_key_formula;
  document.getElementById("summary-decision-formula").textContent = summary.decision_rule_formula;

  const tbody = document.getElementById("summary-phases-tbody");
  tbody.replaceChildren();
  for (const row of summary.phases || []) {
    const tr = document.createElement("tr");

    const tdPhase = document.createElement("td");
    tdPhase.textContent = row.phase;
    const tdComp = document.createElement("td");
    tdComp.textContent = row.complexity;
    const tdOps = document.createElement("td");
    tdOps.textContent = String(row.operations);
    const tdDesc = document.createElement("td");
    tdDesc.textContent = row.description;

    tr.append(tdPhase, tdComp, tdOps, tdDesc);
    tbody.appendChild(tr);
  }
}

function renderPhaseJumps(trace, currentPhase) {
  const bar = document.getElementById("phase-jumps-bar");
  bar.replaceChildren();
  for (const [phaseKey, stepIdx] of Object.entries(trace.phase_offsets)) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "phase-jump-btn" + (phaseKey === currentPhase ? " active" : "");
    btn.textContent = `${PHASE_LABELS[phaseKey] || phaseKey} (#${stepIdx})`;
    btn.addEventListener("click", () => {
      stopAutoPlay();
      goToStep(stepIdx);
    });
    bar.appendChild(btn);
  }
}

function renderVariablesWatch(variables) {
  const grid = document.getElementById("variables-grid");
  grid.replaceChildren();
  for (const [key, val] of Object.entries(variables || {})) {
    const card = document.createElement("div");
    card.className = "var-card";
    const nameEl = document.createElement("div");
    nameEl.className = "var-name";
    nameEl.textContent = key;
    const valEl = document.createElement("div");
    valEl.className = "var-value";
    valEl.textContent = val === null ? "null" : String(val);
    card.append(nameEl, valEl);
    grid.appendChild(card);
  }
}

function renderArraysInspector(step) {
  const container = document.getElementById("arrays-inspector");
  container.replaceChildren();

  if (!step.ordered_ids || step.ordered_ids.length === 0) {
    const note = document.createElement("p");
    note.className = "muted-note";
    note.textContent = "Sem itens viáveis ordenados neste passo.";
    container.appendChild(note);
    return;
  }

  const table = document.createElement("table");
  table.className = "array-table";
  const hasDp = step.dp_table && step.dp_table.length > 0;
  const nPrime = step.ordered_ids.length;
  const startIdx = hasDp ? 0 : 1;

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  const thCorner = document.createElement("th");
  thCorner.textContent = "Vetor / i";
  headRow.appendChild(thCorner);
  for (let i = startIdx; i <= nPrime; i += 1) {
    const th = document.createElement("th");
    th.textContent = String(i);
    if (step.active_dp_index === i) th.classList.add("cell-active");
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");

  const addRow = (label, valueProvider, highlightFn) => {
    const tr = document.createElement("tr");
    const th = document.createElement("th");
    th.textContent = label;
    tr.appendChild(th);
    for (let i = startIdx; i <= nPrime; i += 1) {
      const td = document.createElement("td");
      td.textContent = valueProvider(i);
      const cls = highlightFn ? highlightFn(i) : "";
      if (cls) td.classList.add(cls);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  };

  addRow(
    "Ordered[i]",
    (i) => (i === 0 ? "—" : step.ordered_ids[i - 1]),
    (i) => {
      if (step.active_dp_index === i) return "cell-active";
      if (step.binary_search_range && i > 0) {
        const [lo, mid, hi] = step.binary_search_range;
        if (i - 1 === mid) return "cell-ref";
        if (i - 1 >= lo && i - 1 <= hi) return "cell-bsearch";
      }
      return "";
    }
  );

  addRow(
    "r_i",
    (i) => (i === 0 ? "0" : formatMinutes(step.effective_releases[i - 1])),
    (i) => (step.referenced_dp_index === i ? "cell-ref" : "")
  );

  if (hasDp) {
    addRow(
      "p[i]",
      (i) => (step.predecessors[i] === null ? "?" : String(step.predecessors[i])),
      (i) => (step.active_dp_index === i ? "cell-active" : "")
    );
    addRow(
      "DP[i]",
      (i) => (step.dp_table[i] === null ? "?" : String(step.dp_table[i])),
      (i) => {
        if (step.active_dp_index === i) return "cell-active";
        if (step.referenced_dp_index === i) return "cell-ref";
        return "";
      }
    );
  }

  table.appendChild(tbody);
  container.appendChild(table);
}

function renderCurrentStep() {
  const trace = appState.trace;
  if (!trace || !trace.steps.length) {
    return;
  }
  const step = trace.steps[appState.currentStepIndex];

  document.getElementById("step-counter-badge").textContent =
    `Passo ${step.step_index + 1} / ${trace.steps.length}`;
  document.getElementById("step-slider").value = String(step.step_index);
  document.getElementById("step-phase-badge").textContent =
    PHASE_LABELS[step.phase] || step.phase;
  document.getElementById("step-title").textContent = step.title;
  document.getElementById("step-explanation").textContent = step.explanation;

  document.getElementById("btn-first").disabled = step.step_index === 0;
  document.getElementById("btn-prev").disabled = step.step_index === 0;
  document.getElementById("btn-next").disabled = step.step_index === trace.steps.length - 1;
  document.getElementById("btn-last").disabled = step.step_index === trace.steps.length - 1;

  renderPhaseJumps(trace, step.phase);

  const ganttHost = document.getElementById("gantt-container");
  ganttHost.replaceChildren(
    buildGanttSvg(
      trace.processed_surgeries,
      trace.shift_config,
      step.statuses,
      step.active_surgery_id,
      typeof step.last_release_minutes === "number" ? step.last_release_minutes : null
    )
  );

  renderVariablesWatch(step.variables);
  renderArraysInspector(step);
}

function goToStep(index) {
  if (!appState.trace) return;
  const maxIdx = appState.trace.steps.length - 1;
  appState.currentStepIndex = Math.max(0, Math.min(maxIdx, index));
  renderCurrentStep();
}

function stopAutoPlay() {
  if (appState.autoPlayTimer !== null) {
    clearInterval(appState.autoPlayTimer);
    appState.autoPlayTimer = null;
  }
  document.getElementById("btn-play").textContent = "▶ Auto-Play";
}

function toggleAutoPlay() {
  if (!appState.trace) return;
  if (appState.autoPlayTimer !== null) {
    stopAutoPlay();
    return;
  }
  if (appState.currentStepIndex >= appState.trace.steps.length - 1) {
    goToStep(0);
  }
  const delay = Number(document.getElementById("speed-select").value) || 650;
  document.getElementById("btn-play").textContent = "⏸ Pausar";
  appState.autoPlayTimer = setInterval(() => {
    if (appState.currentStepIndex >= appState.trace.steps.length - 1) {
      stopAutoPlay();
      return;
    }
    goToStep(appState.currentStepIndex + 1);
  }, delay);
}

async function runTraceSimulation() {
  stopAutoPlay();
  showError("");
  try {
    appState.shiftConfig = readShiftConfigFromDom();
    const trace = await postJson("/api/trace", {
      surgeries: appState.surgeries,
      shift_config: appState.shiftConfig,
      algorithm_key: document.getElementById("algo-select").value,
    });
    appState.trace = trace;
    renderComplexitySummary(trace.complexity_summary);
    const slider = document.getElementById("step-slider");
    slider.max = String(Math.max(0, trace.steps.length - 1));
    goToStep(0);
  } catch (err) {
    showError(err.message);
  }
}

async function runComparisonArena() {
  showError("");
  try {
    appState.shiftConfig = readShiftConfigFromDom();
    const data = await postJson("/api/compare", {
      surgeries: appState.surgeries,
      shift_config: appState.shiftConfig,
    });

    const tbody = document.getElementById("compare-summary-tbody");
    tbody.replaceChildren();
    const ganttList = document.getElementById("compare-gantt-list");
    ganttList.replaceChildren();

    const sharedItems = [...appState.surgeries];
    for (const entry of data.entries) {
      sharedItems.push(...entry.selected_surgeries);
    }
    const sharedDomain = computeGanttDomain(sharedItems, appState.shiftConfig);

    for (const entry of data.entries) {
      const tr = document.createElement("tr");

      const tdName = document.createElement("td");
      tdName.textContent = entry.algorithm_name;
      const tdComp = document.createElement("td");
      tdComp.textContent = "O(n log n)";
      const tdSel = document.createElement("td");
      tdSel.textContent = String(entry.total_selected);
      const tdDisc = document.createElement("td");
      tdDisc.textContent = String(entry.discarded_infeasible_count);
      const tdIds = document.createElement("td");
      tdIds.textContent = entry.selected_ids.join(", ") || "—";

      const tdStatus = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = entry.is_physically_valid ? "badge-valid" : "badge-conflict";
      badge.textContent = entry.is_physically_valid
        ? "Válido"
        : `Conflito (${entry.physical_conflicts.length})`;
      tdStatus.appendChild(badge);
      if (!entry.is_physically_valid) {
        const ul = document.createElement("div");
        ul.className = "muted-note";
        ul.textContent = entry.physical_conflicts.join(" | ");
        tdStatus.appendChild(ul);
      }

      tr.append(tdName, tdComp, tdSel, tdDisc, tdIds, tdStatus);
      tbody.appendChild(tr);

      const card = document.createElement("div");
      card.className = "card";
      const title = document.createElement("h3");
      title.textContent = `${entry.algorithm_name} — ${entry.total_selected} selecionada(s) [${entry.selected_ids.join(", ") || "nenhuma"}]`;
      card.appendChild(title);

      const statusMap = {};
      for (const sid of entry.selected_ids) {
        statusMap[sid] = "SELECTED";
      }
      card.appendChild(
        buildGanttSvg(
          entry.selected_surgeries,
          appState.shiftConfig,
          statusMap,
          null,
          null,
          sharedDomain
        )
      );
      ganttList.appendChild(card);
    }
  } catch (err) {
    showError(err.message);
  }
}

function getActiveTabName() {
  const active = document.querySelector(".tab-btn.active");
  return active ? active.dataset.tab : "simulator";
}

function runActiveTabSimulation() {
  const tab = getActiveTabName();
  if (tab === "simulator") {
    runTraceSimulation();
  } else if (tab === "arena") {
    runComparisonArena();
  }
}

async function initApp() {
  try {
    const resp = await fetch("/api/scenarios");
    const data = await resp.json();
    appState.presets = data.scenarios || [];

    const select = document.getElementById("preset-select");
    select.replaceChildren();
    for (const preset of appState.presets) {
      const opt = document.createElement("option");
      opt.value = preset.scenario_id;
      opt.textContent = preset.title;
      select.appendChild(opt);
    }
    const defaultId = appState.presets.some((p) => p.scenario_id === "CASE-02")
      ? "CASE-02"
      : appState.presets[0]?.scenario_id;
    if (defaultId) {
      select.value = defaultId;
      loadPresetById(defaultId);
    }
  } catch (err) {
    showError(`Falha ao carregar cenários: ${err.message}`);
  }

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      stopAutoPlay();
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
      runActiveTabSimulation();
    });
  });

  document.getElementById("preset-select").addEventListener("change", (e) => {
    loadPresetById(e.target.value);
    runActiveTabSimulation();
  });

  document.getElementById("load-preset-btn").addEventListener("click", () => {
    loadPresetById(document.getElementById("preset-select").value);
    runActiveTabSimulation();
  });

  document.getElementById("shift-enabled-checkbox").addEventListener("change", (e) => {
    document.getElementById("shift-fields").classList.toggle("hidden", !e.target.checked);
  });
  document.getElementById("window-enabled-checkbox").addEventListener("change", (e) => {
    document.getElementById("window-fields").classList.toggle("hidden", !e.target.checked);
  });
  document.querySelectorAll(".hhmm-input").forEach(attachHhmmInputMask);

  document.getElementById("horizon-input").addEventListener("input", () => {
    try {
      const minutes = parseHhmmToMinutes(
        document.getElementById("horizon-input").value,
        "Horizonte H"
      );
      document.getElementById("horizon-hhmm").textContent = `${minutes} min`;
    } catch {
      document.getElementById("horizon-hhmm").textContent = "-- min";
    }
  });

  document.getElementById("new-type").addEventListener("change", (e) => {
    const sterInput = document.getElementById("new-sterilization");
    const isContam = e.target.value === "CONTAMINATED";
    sterInput.disabled = !isContam;
    sterInput.value = isContam ? "30" : "0";
  });

  document.getElementById("add-surgery-form").addEventListener("submit", (e) => {
    e.preventDefault();
    showError("");
    try {
      const surgeryId = document.getElementById("new-id").value.trim();
      if (!surgeryId) {
        throw new Error("Informe um identificador válido para a cirurgia.");
      }
      if (appState.surgeries.some((item) => item.surgery_id === surgeryId)) {
        throw new Error(`Já existe uma cirurgia com o ID '${surgeryId}'.`);
      }

      const startTime = parseHhmmToMinutes(
        document.getElementById("new-start").value,
        "Início da cirurgia"
      );
      const finishTime = parseHhmmToMinutes(
        document.getElementById("new-finish").value,
        "Fim da cirurgia"
      );
      if (startTime >= finishTime) {
        throw new Error(
          `Horário inválido para '${surgeryId}': o início (${formatMinutes(startTime)}) deve ser estritamente menor que o término (${formatMinutes(finishTime)}).`
        );
      }

      const sType = document.getElementById("new-type").value;
      const sterilization =
        sType === "CONTAMINATED"
          ? Number(document.getElementById("new-sterilization").value)
          : 0;
      if (
        sType === "CONTAMINATED" &&
        (!Number.isInteger(sterilization) || sterilization <= 0)
      ) {
        throw new Error(
          "Cirurgias contaminadas exigem duração inteira de esterilização maior que zero."
        );
      }

      appState.surgeries.push({
        surgery_id: surgeryId,
        start_time: startTime,
        finish_time: finishTime,
        surgery_type: sType,
        sterilization_duration: sterilization,
      });
      renderSurgeriesEditorTable();
      e.target.reset();
      document.getElementById("new-sterilization").value = "0";
      document.getElementById("new-sterilization").disabled = true;
      runActiveTabSimulation();
    } catch (err) {
      showError(err.message);
    }
  });

  document.getElementById("apply-input-btn").addEventListener("click", runActiveTabSimulation);
  document.getElementById("algo-select").addEventListener("change", runTraceSimulation);
  document.getElementById("run-compare-btn").addEventListener("click", runComparisonArena);

  document.getElementById("btn-first").addEventListener("click", () => { stopAutoPlay(); goToStep(0); });
  document.getElementById("btn-prev").addEventListener("click", () => { stopAutoPlay(); goToStep(appState.currentStepIndex - 1); });
  document.getElementById("btn-next").addEventListener("click", () => { stopAutoPlay(); goToStep(appState.currentStepIndex + 1); });
  document.getElementById("btn-last").addEventListener("click", () => {
    stopAutoPlay();
    if (appState.trace) goToStep(appState.trace.steps.length - 1);
  });
  document.getElementById("btn-play").addEventListener("click", toggleAutoPlay);
  document.getElementById("step-slider").addEventListener("input", (e) => {
    stopAutoPlay();
    goToStep(Number(e.target.value));
  });

  await runTraceSimulation();
}

document.addEventListener("DOMContentLoaded", initApp);
