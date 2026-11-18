/* Motor interativo do simulador, arena comparativa e gráficos SVG sem dependências */

const SVG_NS = "http://www.w3.org/2000/svg";

const PHASE_LABELS = {
  PREPROCESSING: "Pré-processamento",
  SORTING: "Ordenação",
  PREDECESSORS: "Predecessores p[i]",
  SELECTION_OR_DP: "Seleção / DP",
  BACKTRACKING: "Backtracking",
  RESULT: "Resultado",
};

const SERIES_COLORS = {
  "Classic Greedy (Earliest Finish Time)": "#64748b",
  "Classic Dynamic Programming": "#0284c7",
  "Naive Static Reduction (f'_i = f_i + c_i)": "#dc2626",
  "Adapted Greedy (Earliest Effective Release)": "#16a34a",
  "Adapted Dynamic Programming": "#7c3aed",
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
  const horizon = Number(document.getElementById("horizon-input").value);
  const windowEnabled = document.getElementById("window-enabled-checkbox").checked;
  let shiftWindow = null;
  if (windowEnabled) {
    shiftWindow = {
      start: Number(document.getElementById("window-start-input").value),
      end: Number(document.getElementById("window-end-input").value),
    };
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
  horizonInput.value = String(shiftConfig.closing_horizon);
  horizonHhmm.textContent = formatMinutes(shiftConfig.closing_horizon);

  if (shiftConfig.shift_window) {
    windowCheckbox.checked = true;
    windowFields.classList.remove("hidden");
    document.getElementById("window-start-input").value = String(shiftConfig.shift_window.start);
    document.getElementById("window-end-input").value = String(shiftConfig.shift_window.end);
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

function buildGanttSvg(items, shiftConfig, statuses = {}, activeId = null, lastRelease = null) {
  const width = 900;
  const margin = { top: 28, right: 30, bottom: 26, left: 110 };
  const rowHeight = 28;
  const height = Math.max(120, margin.top + margin.bottom + Math.max(1, items.length) * rowHeight);

  let minT = Infinity;
  let maxT = -Infinity;
  for (const item of items) {
    minT = Math.min(minT, item.start_time);
    maxT = Math.max(maxT, item.finish_time + item.sterilization_duration, item.effective_release_time);
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
  const pad = Math.max(30, Math.round((maxT - minT) * 0.08));
  const domainStart = Math.max(0, minT - pad);
  const domainEnd = maxT + pad;
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
      typeof step.variables.last_release === "number" ? step.variables.last_release : null
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
      is_presorted: document.getElementById("presorted-checkbox").checked,
    });
    appState.trace = trace;
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
      is_presorted: document.getElementById("presorted-checkbox").checked,
    });

    const tbody = document.getElementById("compare-summary-tbody");
    tbody.replaceChildren();
    const ganttList = document.getElementById("compare-gantt-list");
    ganttList.replaceChildren();

    for (const entry of data.entries) {
      const tr = document.createElement("tr");

      const tdName = document.createElement("td");
      tdName.textContent = entry.algorithm_name;
      const tdSel = document.createElement("td");
      tdSel.textContent = String(entry.total_selected);
      const tdDisc = document.createElement("td");
      tdDisc.textContent = String(entry.discarded_infeasible_count);
      const tdIds = document.createElement("td");
      tdIds.textContent = entry.selected_ids.join(", ") || "—";
      const tdNs = document.createElement("td");
      tdNs.textContent = String(entry.elapsed_ns);

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

      tr.append(tdName, tdSel, tdDisc, tdIds, tdNs, tdStatus);
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
      card.appendChild(buildGanttSvg(entry.selected_surgeries, appState.shiftConfig, statusMap));
      ganttList.appendChild(card);
    }
  } catch (err) {
    showError(err.message);
  }
}

function buildLineChartSvg(points, valueKey, yLabel) {
  const width = 560;
  const height = 280;
  const margin = { top: 24, right: 20, bottom: 58, left: 60 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  const sizes = [...new Set(points.map((p) => p.input_size))].sort((a, b) => a - b);
  const algos = [...new Set(points.map((p) => p.algorithm_name))];

  const minX = Math.min(...sizes);
  const maxX = Math.max(...sizes, minX + 1);
  const maxY = Math.max(0.0001, ...points.map((p) => Number(p[valueKey]) || 0));

  const scaleX = (x) => margin.left + ((x - minX) / Math.max(1, maxX - minX)) * plotW;
  const scaleY = (y) => margin.top + plotH - (y / maxY) * plotH;

  const svg = createSvgElement("svg", {
    viewBox: `0 0 ${width} ${height}`,
    width: "100%",
    style: "display: block; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;",
  });

  // Eixos
  svg.appendChild(createSvgElement("line", {
    x1: margin.left, y1: margin.top, x2: margin.left, y2: margin.top + plotH, stroke: "#475569",
  }));
  svg.appendChild(createSvgElement("line", {
    x1: margin.left, y1: margin.top + plotH, x2: margin.left + plotW, y2: margin.top + plotH, stroke: "#475569",
  }));

  for (let i = 0; i <= 4; i += 1) {
    const valY = (maxY * i) / 4;
    const y = scaleY(valY);
    svg.appendChild(createSvgElement("line", {
      x1: margin.left, y1: y, x2: margin.left + plotW, y2: y, stroke: "#f1f5f9",
    }));
    const lbl = createSvgElement("text", {
      x: margin.left - 6, y: y + 4, "text-anchor": "end", "font-size": "10", fill: "#64748b",
    });
    lbl.textContent = valY >= 100 ? valY.toFixed(0) : valY.toFixed(2);
    svg.appendChild(lbl);
  }

  for (const s of sizes) {
    const x = scaleX(s);
    const lbl = createSvgElement("text", {
      x, y: margin.top + plotH + 15, "text-anchor": "middle", "font-size": "10", fill: "#64748b",
    });
    lbl.textContent = String(s);
    svg.appendChild(lbl);
  }

  const yTitle = createSvgElement("text", {
    x: margin.left, y: 14, "font-size": "11", "font-weight": "700", fill: "#1e293b",
  });
  yTitle.textContent = yLabel;
  svg.appendChild(yTitle);

  algos.forEach((algo, idx) => {
    const color = SERIES_COLORS[algo] || "#334155";
    const seriesPoints = points
      .filter((p) => p.algorithm_name === algo)
      .sort((a, b) => a.input_size - b.input_size);

    const coords = seriesPoints.map((p) => `${scaleX(p.input_size)},${scaleY(Number(p[valueKey]) || 0)}`).join(" ");
    svg.appendChild(createSvgElement("polyline", {
      fill: "none",
      stroke: color,
      "stroke-width": "2.4",
      points: coords,
    }));
    for (const p of seriesPoints) {
      svg.appendChild(createSvgElement("circle", {
        cx: scaleX(p.input_size),
        cy: scaleY(Number(p[valueKey]) || 0),
        r: "3.5",
        fill: color,
      }));
    }

    const legX = margin.left + (idx % 2) * 245;
    const legY = height - 24 + Math.floor(idx / 2) * 14;
    svg.appendChild(createSvgElement("rect", { x: legX, y: legY - 8, width: "10", height: "10", fill: color }));
    const legTxt = createSvgElement("text", { x: legX + 14, y: legY, "font-size": "10", fill: "#1e293b" });
    legTxt.textContent = algo;
    svg.appendChild(legTxt);
  });

  return svg;
}

async function runBenchmarkSuite() {
  showError("");
  try {
    const rawSizes = document
      .getElementById("bench-sizes")
      .value.split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number);

    const isPresorted = document.getElementById("bench-presorted").checked;
    const data = await postJson("/api/benchmark", {
      sizes: rawSizes,
      repetitions: Number(document.getElementById("bench-reps").value),
      seed: Number(document.getElementById("bench-seed").value),
      is_presorted: isPresorted,
      include_naive: document.getElementById("bench-include-naive").checked,
      shift_config: readShiftConfigFromDom(),
    });

    document.getElementById("benchmark-table-pre").textContent = data.table;
    document.getElementById("chart-time-container").replaceChildren(
      buildLineChartSvg(data.points, "median_elapsed_ms", "Mediana (ms)")
    );
    const ratioKey = isPresorted ? "ratio_n" : "ratio_n_log_n";
    document.getElementById("chart-ratio-title").textContent = isPresorted
      ? "Razão Normalizada T(n) / n (ns)"
      : "Razão Normalizada T(n) / (n log2 n) (ns)";
    document.getElementById("chart-ratio-container").replaceChildren(
      buildLineChartSvg(data.points, ratioKey, isPresorted ? "T(n)/n (ns)" : "T(n)/(n log2 n) (ns)")
    );
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
    const defaultId = appState.presets.some((p) => p.scenario_id === "SC-02")
      ? "SC-02"
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
  document.getElementById("horizon-input").addEventListener("input", (e) => {
    const v = Number(e.target.value);
    document.getElementById("horizon-hhmm").textContent = Number.isFinite(v) && v >= 0 ? formatMinutes(v) : "--:--";
  });

  document.getElementById("new-type").addEventListener("change", (e) => {
    const sterInput = document.getElementById("new-sterilization");
    const isContam = e.target.value === "CONTAMINATED";
    sterInput.disabled = !isContam;
    sterInput.value = isContam ? "30" : "0";
  });

  document.getElementById("add-surgery-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const sType = document.getElementById("new-type").value;
    appState.surgeries.push({
      surgery_id: document.getElementById("new-id").value.trim(),
      start_time: Number(document.getElementById("new-start").value),
      finish_time: Number(document.getElementById("new-finish").value),
      surgery_type: sType,
      sterilization_duration: sType === "CONTAMINATED" ? Number(document.getElementById("new-sterilization").value) : 0,
    });
    renderSurgeriesEditorTable();
    e.target.reset();
    document.getElementById("new-sterilization").value = "0";
    document.getElementById("new-sterilization").disabled = true;
    runActiveTabSimulation();
  });

  document.getElementById("generate-btn").addEventListener("click", async () => {
    showError("");
    try {
      const cfg = readShiftConfigFromDom();
      const data = await postJson("/api/generate", {
        n: Number(document.getElementById("gen-n").value),
        seed: Number(document.getElementById("gen-seed").value),
        contaminated_ratio: Number(document.getElementById("gen-ratio").value),
        horizon: cfg ? cfg.closing_horizon : 1080,
      });
      appState.surgeries = data.surgeries;
      renderSurgeriesEditorTable();
      runActiveTabSimulation();
    } catch (err) {
      showError(err.message);
    }
  });

  document.getElementById("apply-input-btn").addEventListener("click", runActiveTabSimulation);
  document.getElementById("algo-select").addEventListener("change", runTraceSimulation);
  document.getElementById("presorted-checkbox").addEventListener("change", runActiveTabSimulation);
  document.getElementById("run-compare-btn").addEventListener("click", runComparisonArena);
  document.getElementById("run-benchmark-btn").addEventListener("click", runBenchmarkSuite);

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
