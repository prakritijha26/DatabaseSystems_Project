// src/app.ts
var el = (id) => {
  const element = document.getElementById(id);
  if (!element)
    throw new Error(`Missing interface element: ${id}`);
  return element;
};
var text = (id, value) => {
  el(id).textContent = value;
};
var input = el("query-input");
var execute = el("execute-btn");
var busy = false;
var history = [];
var historyIndex = 0;
var draft = "";
function lineNumbers() {
  text("line-numbers", input.value.split(`
`).map((_, i) => String(i + 1).padStart(2, "0")).join(`
`));
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}
input.addEventListener("input", () => {
  historyIndex = history.length;
  draft = input.value;
  lineNumbers();
});
input.addEventListener("keydown", (event) => {
  if (event.isComposing)
    return;
  if (event.key === "Enter" && (!event.shiftKey || event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    el("query-form").requestSubmit();
    return;
  }
  const singleLine = !input.value.includes(`
`);
  const noSelection = input.selectionStart === input.selectionEnd;
  const previous = event.key === "ArrowUp" && (singleLine || input.selectionStart === 0);
  const next = event.key === "ArrowDown" && (singleLine || input.selectionEnd === input.value.length);
  if (!noSelection || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey || !previous && !next)
    return;
  event.preventDefault();
  if (historyIndex === history.length)
    draft = input.value;
  historyIndex = Math.max(0, Math.min(history.length, historyIndex + (previous ? -1 : 1)));
  input.value = historyIndex === history.length ? draft : history[historyIndex];
  const cursor = previous ? 0 : input.value.length;
  input.setSelectionRange(cursor, cursor);
  lineNumbers();
});
function cellRow(values, parent) {
  const row = document.createElement("tr");
  values.forEach((value) => {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(cell);
  });
  parent.append(row);
}
function emptyRow(message, columns, parent) {
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = columns;
  cell.className = "empty";
  cell.textContent = message;
  row.append(cell);
  parent.append(row);
}
function display(value) {
  return typeof value === "number" ? value.toFixed(2) : value == null ? "—" : String(value);
}
function delta(value) {
  return typeof value === "number" ? `${value > 0 ? "+" : ""}${value.toFixed(2)}` : display(value);
}
function context(metric) {
  return `Student ${metric.student_id ?? "—"}${metric.course_code ? " / " + metric.course_code : ""}`;
}
function resetMetrics() {
  ["att-before", "att-after", "attendance-delta", "elig-before", "score-before", "score-after", "score-delta"].forEach((id) => text(id, "—"));
  text("elig-after", "NOT EVALUATED");
  el("elig-after").className = "pill";
  text("score-title", "DEMO GPA DELTA");
  text("score-note", "No GPA metric change supplied.");
  text("attendance-context", "No attendance metric supplied.");
  el("attendance-bar").replaceChildren();
  el("attendance-bar").style.width = "0%";
  el("attendance-meter").removeAttribute("aria-valuenow");
  el("attendance-meter").setAttribute("aria-valuetext", "No attendance result");
  el("metric-rows").replaceChildren();
}
function render(report) {
  resetMetrics();
  const offline = report.engine_backend === "mock";
  const committed = !offline && report.status === "COMMITTED" && report.committed === true;
  text("report-status", report.status === "ERROR" ? "EXECUTION REJECTED / FAILED" : offline ? "OFFLINE DEMO" : committed ? "PERMANENTLY COMMITTED" : report.status === "VERIFIED_PRISTINE" ? "VERIFICATION COMPLETE" : "SIMULATION COMPLETE");
  el("report-status").style.color = committed ? "var(--gold)" : "";
  text("backend", offline ? "BACKEND / OFFLINE FIXTURES" : "BACKEND / LIVE POSTGRESQL");
  text("execution-time", `${report.execution_time_ms.toFixed(2)} ms`);
  text("report-message", report.error_message ?? (offline ? "PostgreSQL unavailable. Illustrative fixture data only; your SQL was not executed." : committed ? report.message ?? "Changes permanently committed to PostgreSQL." : report.ddl_mode === "CASCADE_PREVIEW" ? "Original DROP COLUMN was blocked. Showing an explicitly expanded CASCADE preview; schema restored." : "Results captured inside a repeatable-read transaction."));
  const tables = el("table-rows");
  tables.replaceChildren();
  report.tables_affected.forEach((table) => cellRow([table.table, table.action ?? "CHANGED", String(table.rows_changed)], tables));
  if (!report.tables_affected.length)
    emptyRow(report.status === "ERROR" ? "No successful changes reported." : "No changed relations reported.", 3, tables);
  text("row-count", `${report.tables_affected.reduce((sum, table) => sum + table.rows_changed, 0)} ROWS`);
  report.metrics.forEach((metric) => cellRow([context(metric), metric.metric, display(metric.before), display(metric.after), delta(metric.change)], el("metric-rows")));
  if (!report.metrics.length)
    emptyRow("No academic metric changes reported.", 5, el("metric-rows"));
  const attendance = report.metrics.find((m) => m.metric === "attendance_percentage");
  const eligibility = report.metrics.find((m) => m.metric === "exam_eligibility" && (!attendance || m.student_id === attendance.student_id && m.course_code === attendance.course_code));
  const score = report.metrics.find((m) => m.metric === "weighted_gpa" || m.metric === "cgpa") ?? report.metrics.find((m) => m.metric === "weighted_average_score");
  if (attendance) {
    text("att-before", display(attendance.before));
    text("att-after", display(attendance.after));
    text("attendance-delta", delta(attendance.change));
    text("attendance-context", context(attendance) + " / % attendance");
    if (typeof attendance.after === "number") {
      const percent = Math.max(0, Math.min(100, attendance.after));
      const bar = el("attendance-bar");
      bar.style.width = `${percent}%`;
      for (let i = 0;i < Math.ceil(percent / 2.5); i++) {
        const segment = document.createElement("span");
        segment.className = "segment";
        if (percent < 75)
          segment.style.background = "var(--red)";
        bar.append(segment);
      }
      el("attendance-meter").setAttribute("aria-valuenow", String(percent));
      el("attendance-meter").setAttribute("aria-valuetext", `${percent}% attendance`);
    }
  }
  if (eligibility) {
    text("elig-before", display(eligibility.before));
    text("elig-after", display(eligibility.after));
    el("elig-after").className = `pill ${eligibility.after === "ELIGIBLE" ? "positive" : eligibility.after === "INELIGIBLE" ? "negative" : ""}`;
  }
  if (score) {
    text("score-title", score.metric === "weighted_gpa" ? "DEMO GPA DELTA" : score.metric === "cgpa" ? "CGPA DELTA" : "WEIGHTED SCORE DELTA");
    text("score-before", display(score.before));
    text("score-after", display(score.after));
    text("score-delta", delta(score.change));
    text("score-note", context(score) + (score.metric === "weighted_gpa" ? " / demonstration grade bands, not official VIT policy" : score.metric === "cgpa" ? " / credit-weighted CGPA" : " / score out of 100"));
  }
  const dependencies = el("dependencies");
  dependencies.replaceChildren();
  text("dependency-count", `${report.broken_dependencies.length} REPORTED`);
  report.broken_dependencies.forEach((dep) => {
    const block = document.createElement("div");
    block.className = "dependency";
    const title = document.createElement("strong");
    title.textContent = `${dep.object_type} / ${dep.object_name}`;
    const reason = document.createElement("p");
    reason.textContent = dep.reason;
    block.append(title, reason);
    dependencies.append(block);
  });
  if (!report.broken_dependencies.length) {
    const note = document.createElement("p");
    note.className = "empty";
    note.textContent = offline ? "No dependency alerts in this fixture." : "No catalog-recorded dependencies reported for this operation.";
    dependencies.append(note);
  }
  el("query-results").hidden = !report.query_columns;
  el("query-head").replaceChildren();
  el("query-rows").replaceChildren();
  if (report.query_columns) {
    cellRow(report.query_columns, el("query-head"));
    (report.query_rows ?? []).forEach((row) => cellRow(row.map((value) => value === null ? "NULL" : String(value)), el("query-rows")));
    text("query-caption", report.query_truncated ? "First 500 rows shown." : "Read-only SELECT result");
  }
  text("execution-log", report.logs.join(`
`));
  text("interlock-label", offline ? "INTERLOCK / OFFLINE" : committed ? "INTERLOCK / COMMITTED (PERMANENT)" : report.rolled_back ? "INTERLOCK / ROLLED BACK" : "INTERLOCK / UNCONFIRMED");
  el("interlock-label").style.color = committed ? "var(--gold)" : "";
  text("interlock-message", offline ? "Zero database writes: no SQL was executed or persisted." : committed ? "Permanent write: Changes committed to database storage." : report.rolled_back ? "Transaction changes discarded. Rollback confirmed by PostgreSQL." : "No successful rollback claim is made for this result.");
}
el("query-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy)
    return;
  const sql = input.value.trim();
  if (!sql) {
    text("report-message", "Enter a SQL statement first.");
    input.focus();
    return;
  }
  busy = true;
  execute.disabled = true;
  document.querySelector(".results")?.setAttribute("aria-busy", "true");
  text("execution-log", "Awaiting execution report…");
  text("report-status", "RUNNING");
  text("interlock-label", "INTERLOCK / PENDING");
  text("interlock-message", "Awaiting response.");
  try {
    const response = await fetch("/api/whatif", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sql }), signal: AbortSignal.timeout(15000) });
    if (!response.ok)
      throw new Error(`Request failed (HTTP ${response.status}).`);
    const report = await response.json();
    if (!Array.isArray(report.metrics) || !Array.isArray(report.tables_affected) || !Array.isArray(report.broken_dependencies) || !Array.isArray(report.logs) || typeof report.execution_time_ms !== "number")
      throw new Error("The server returned an invalid impact report.");
    render(report);
    if (report.status !== "ERROR") {
      const duplicate = history.indexOf(sql);
      if (duplicate !== -1)
        history.splice(duplicate, 1);
      history.push(sql);
      historyIndex = history.length;
      if (input.value.trim() === sql)
        input.value = "";
      draft = input.value;
      lineNumbers();
    }
  } catch (error) {
    resetMetrics();
    el("query-results").hidden = true;
    text("report-status", "REQUEST FAILED");
    text("report-message", error instanceof Error ? error.message : "Unable to reach the server.");
    text("backend", "BACKEND / RESPONSE UNAVAILABLE");
    text("execution-time", "— ms");
    el("table-rows").replaceChildren();
    emptyRow("No result received.", 3, el("table-rows"));
    text("row-count", "— ROWS");
    text("dependencies", "No result received.");
    text("dependency-count", "—");
    text("execution-log", "Request failed; server outcome is unknown.");
    text("interlock-label", "INTERLOCK / UNCONFIRMED");
    text("interlock-message", "No response received. Database outcome is unknown.");
  } finally {
    busy = false;
    execute.disabled = false;
    input.focus();
    document.querySelector(".results")?.setAttribute("aria-busy", "false");
  }
});
lineNumbers();
