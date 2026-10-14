// src/app.ts
var reviewQueries = [
  "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;",
  "WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';",
  "WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';",
  "WHAT_IF ALTER TABLE marks DROP COLUMN score;",
  "WHAT_IF COMMIT;",
  "SELECT student_id, name, attendance_pct, cgpa, exam_eligible FROM student_summary_view WHERE student_id = 1042;"
];
var liveQueries = [
  "WHAT_IF UPDATE attendance SET classes_attended = 20 WHERE enrollment_id = 1;",
  "WHAT_IF UPDATE marks SET score = 45 WHERE enrollment_id = 1;",
  "WHAT_IF DELETE FROM enrollments WHERE enrollment_id = 1;",
  reviewQueries[3],
  reviewQueries[4],
  "SELECT student_id, student_name, course_code, attendance_percentage, exam_eligible FROM attendance_eligibility WHERE student_id = 1001;"
];
var hints = [
  "Compare attendance and exam eligibility against the 75% threshold.",
  "Inspect the academic metric change after a mark adjustment.",
  "Inspect deleted enrollment rows and dependent attendance / marks.",
  "Inspect reverse dependencies. Live DDL is not yet supported; offline results are fixtures.",
  "Test rejection of explicit transaction control.",
  "Inspect baseline data. Live SELECT is not yet supported; offline results are fixtures."
];
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
var querySet = el("query-set");
var tracks = document.querySelectorAll(".track");
var selected = 0;
var busy = false;
function lineNumbers() {
  text("line-numbers", input.value.split(`
`).map((_, i) => String(i + 1).padStart(2, "0")).join(`
`));
}
function cue(index) {
  selected = index;
  input.value = (querySet.value === "live" ? liveQueries : reviewQueries)[index];
  tracks.forEach((button, i) => {
    button.classList.toggle("active", index === i);
    button.setAttribute("aria-pressed", String(index === i));
  });
  text("scenario-hint", hints[index] + (querySet.value === "review" ? " Review queries use the original demo schema; select Delivered schema for live DML." : " Uses the delivered enrollment-based schema. Offline fallback shows illustrative review fixtures."));
  lineNumbers();
}
tracks.forEach((button, i) => button.addEventListener("click", () => cue(i)));
querySet.addEventListener("change", () => cue(selected));
input.addEventListener("input", () => {
  lineNumbers();
  tracks.forEach((button) => {
    button.classList.remove("active");
    button.setAttribute("aria-pressed", "false");
  });
});
input.addEventListener("scroll", () => {
  el("line-numbers").scrollTop = input.scrollTop;
});
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    el("query-form").requestSubmit();
  }
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
  text("score-title", "CGPA DELTA");
  text("score-note", "No CGPA metric supplied.");
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
  text("report-status", report.status === "ERROR" ? "EXECUTION REJECTED / FAILED" : offline ? "OFFLINE DEMO" : "SIMULATION COMPLETE");
  text("backend", offline ? "BACKEND / OFFLINE FIXTURES" : "BACKEND / LIVE POSTGRESQL");
  text("execution-time", `${report.execution_time_ms.toFixed(2)} ms`);
  text("report-message", report.error_message ?? (offline ? "PostgreSQL unavailable. Illustrative fixture data only; your SQL was not executed." : "Results captured inside a repeatable-read transaction."));
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
  const score = report.metrics.find((m) => m.metric === "cgpa" || m.metric === "weighted_average_score");
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
    text("score-title", score.metric === "cgpa" ? "CGPA DELTA" : "WEIGHTED SCORE DELTA");
    text("score-before", display(score.before));
    text("score-after", display(score.after));
    text("score-delta", delta(score.change));
    text("score-note", context(score) + (score.metric === "cgpa" ? " / credit-weighted CGPA" : " / score out of 100, not institutional CGPA"));
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
    note.textContent = offline ? "No dependency alerts in this fixture." : "Catalog tracing is not available in the live DML engine.";
    dependencies.append(note);
  }
  text("execution-log", report.logs.join(`
`));
  text("interlock-label", offline ? "INTERLOCK / OFFLINE" : report.rolled_back ? "INTERLOCK / ROLLED BACK" : "INTERLOCK / UNCONFIRMED");
  text("interlock-message", offline ? "Zero database writes: no SQL was executed." : report.rolled_back ? "Transaction changes discarded. Rollback confirmed by PostgreSQL." : "No successful rollback claim is made for this result.");
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
  querySet.disabled = true;
  tracks.forEach((button) => button.disabled = true);
  document.querySelector(".results")?.setAttribute("aria-busy", "true");
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
  } catch (error) {
    resetMetrics();
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
    querySet.disabled = false;
    tracks.forEach((button) => button.disabled = false);
    document.querySelector(".results")?.setAttribute("aria-busy", "false");
  }
});
cue(0);
