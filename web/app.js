// src/app.ts
var SCENARIOS = {
  "1": {
    number: 1,
    id: "1",
    title: "Attendance Deletion (Eligibility Flip)",
    sql: "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;",
    hint: "Track 1: Deletes 14 attendance records for student 1042 -> Attendance falls below 75% -> Exam eligibility flips from ELIGIBLE to INELIGIBLE."
  },
  "2": {
    number: 2,
    id: "2",
    title: "Mark Update (CGPA Recalculation)",
    sql: "WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';",
    hint: "Track 2: Modifies student 1042's CSE202 mark -> Credit-weighted CGPA recalculated in snapshot -> Numerical delta displayed."
  },
  "3": {
    number: 3,
    id: "3",
    title: "Course Deregistration (Cascades)",
    sql: "WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';",
    hint: "Track 3: Course deregistration -> Foreign key constraints trigger ON DELETE CASCADE into attendance (26 rows) and marks (3 rows)."
  },
  "4": {
    number: 4,
    id: "4",
    title: "Drop Column (Catalog Reverse Dependency)",
    sql: "WHAT_IF ALTER TABLE marks DROP COLUMN score;",
    hint: "Track 4: Hypothetical DDL -> Queries pg_depend and pg_rewrite catalogs -> Traces broken CGPA views and failing metric queries."
  },
  "5": {
    number: 5,
    id: "5",
    title: "Sandbox Security Filter",
    sql: "WHAT_IF COMMIT;",
    hint: "Track 5: Sandbox security filter -> Rejects COMMIT to guarantee the transaction snapshot can never escape."
  },
  "6": {
    number: 6,
    id: "6",
    title: "Post-Simulation Immutability Verification",
    sql: "SELECT student_id, name, attendance_pct, cgpa, exam_eligible FROM student_summary_view WHERE student_id = 1042;",
    hint: "Track 6: Post-simulation audit -> Runs direct SELECT against PostgreSQL proving live tables remain 100% pristine."
  }
};
document.addEventListener("DOMContentLoaded", () => {
  const terminalScreen = document.getElementById("terminal-screen");
  const terminalOutput = document.getElementById("terminal-output");
  const queryInput = document.getElementById("query-input");
  const clearTermBtn = document.getElementById("clear-term-btn");
  const scenarioInfoText = document.getElementById("scenario-info-text");
  const channelButtons = document.querySelectorAll(".channel-btn");
  const reportStatusBadge = document.getElementById("report-status-badge");
  const metaType = document.getElementById("meta-type");
  const metaMode = document.getElementById("meta-mode");
  const metaTime = document.getElementById("meta-time");
  const metaSql = document.getElementById("meta-sql");
  const totalRowsBadge = document.getElementById("total-rows-badge");
  const tablesAffectedList = document.getElementById("tables-affected-list");
  const metricsSection = document.getElementById("metrics-section");
  const attBefore = document.getElementById("att-before");
  const attAfter = document.getElementById("att-after");
  const attendanceDeltaBadge = document.getElementById("attendance-delta-badge");
  const attendanceBar = document.getElementById("attendance-bar");
  const eligBefore = document.getElementById("elig-before");
  const eligAfter = document.getElementById("elig-after");
  const eligReason = document.getElementById("elig-reason");
  const eligibilityStatusBadge = document.getElementById("eligibility-status-badge");
  const cgpaBefore = document.getElementById("cgpa-before");
  const cgpaAfter = document.getElementById("cgpa-after");
  const cgpaDeltaBadge = document.getElementById("cgpa-delta-badge");
  const cgpaNote = document.getElementById("cgpa-note");
  const schemaSection = document.getElementById("schema-section");
  const brokenCountBadge = document.getElementById("broken-count-badge");
  const brokenDependenciesList = document.getElementById("broken-dependencies-list");
  const commandHistory = [];
  let historyIndex = -1;
  terminalScreen.addEventListener("click", () => {
    queryInput.focus();
  });
  queryInput.focus();
  if (clearTermBtn) {
    clearTermBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      clearTerminal();
    });
  }
  function clearTerminal() {
    terminalOutput.innerHTML = "";
    queryInput.value = "";
    queryInput.focus();
  }
  channelButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      channelButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const scId = btn.dataset.scenario;
      if (scId && SCENARIOS[scId]) {
        const sc = SCENARIOS[scId];
        scenarioInfoText.textContent = sc.hint;
        executeCommand(sc.sql);
      }
    });
  });
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const rawCmd = queryInput.value.trim();
      if (!rawCmd)
        return;
      commandHistory.push(rawCmd);
      historyIndex = commandHistory.length;
      queryInput.value = "";
      executeCommand(rawCmd);
    } else if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex--;
        queryInput.value = commandHistory[historyIndex];
      }
      e.preventDefault();
    } else if (e.key === "ArrowDown") {
      if (historyIndex < commandHistory.length - 1) {
        historyIndex++;
        queryInput.value = commandHistory[historyIndex];
      } else {
        historyIndex = commandHistory.length;
        queryInput.value = "";
      }
      e.preventDefault();
    }
  });
  async function executeCommand(cmd) {
    appendTerminalLine(cmd);
    const lower = cmd.toLowerCase().trim();
    if (lower === "clear" || lower === "cls") {
      clearTerminal();
      return;
    }
    if (lower === "help") {
      printHelp();
      scrollTerminalToBottom();
      return;
    }
    if (lower === "scenarios" || lower === "tracks" || lower === "list") {
      printScenariosList();
      scrollTerminalToBottom();
      return;
    }
    if (/^[1-6]$/.test(lower)) {
      const sc = SCENARIOS[lower];
      scenarioInfoText.textContent = sc.hint;
      channelButtons.forEach((b) => {
        b.classList.toggle("active", b.dataset.scenario === lower);
      });
      printSystemNotice(`Cued Track #${lower}: ${sc.sql}`);
      await runSimulationRequest(sc.sql);
      return;
    }
    if (lower === "status") {
      printStatus();
      scrollTerminalToBottom();
      return;
    }
    await runSimulationRequest(cmd);
  }
  function appendTerminalLine(cmd) {
    const entry = document.createElement("div");
    entry.className = "term-entry";
    entry.innerHTML = `
      <div class="term-cmd-line">
        <span class="crt-prompt-sign">whatif&gt;</span>
        <span class="term-cmd-text">${escapeHtml(cmd)}</span>
      </div>
    `;
    terminalOutput.appendChild(entry);
    scrollTerminalToBottom();
  }
  function printSystemNotice(text) {
    const div = document.createElement("div");
    div.style.color = "var(--c-cyan)";
    div.style.fontSize = "0.74rem";
    div.style.margin = "3px 0 3px 12px";
    div.textContent = `[TRACK CUE] ${text}`;
    terminalOutput.appendChild(div);
  }
  function printHelp() {
    const box = document.createElement("div");
    box.className = "term-report-box";
    box.innerHTML = `
      <div class="term-report-title"><span>WHAT-IF DATABASE CONSOLE COMMANDS</span></div>
      <table class="term-ascii-table">
        <tr><th>Command</th><th>Operation</th></tr>
        <tr><td><code>WHAT_IF &lt;sql&gt;</code></td><td>Execute snapshot simulation (REPEATABLE READ; always rolled back)</td></tr>
        <tr><td><code>SELECT &lt;sql&gt;</code></td><td>Query live PostgreSQL tables to verify zero persistent writes</td></tr>
        <tr><td><code>1</code> ... <code>6</code></td><td>Quick-run review tracks 1 through 6</td></tr>
        <tr><td><code>tracks</code> / <code>scenarios</code></td><td>Display all 6 evaluation scenarios</td></tr>
        <tr><td><code>status</code></td><td>Inspect transaction sandbox and storage interlock</td></tr>
        <tr><td><code>clear</code></td><td>Clear terminal screen</td></tr>
      </table>
    `;
    terminalOutput.appendChild(box);
  }
  function printScenariosList() {
    const box = document.createElement("div");
    box.className = "term-report-box";
    let rowsHtml = "";
    Object.keys(SCENARIOS).forEach((num) => {
      rowsHtml += `
        <tr>
          <td><strong style="color:var(--c-gold)">TRK-${num}</strong></td>
          <td><code>${escapeHtml(SCENARIOS[num].sql)}</code></td>
        </tr>
      `;
    });
    box.innerHTML = `
      <div class="term-report-title"><span>OFFICIAL REVIEW TRACKS (Type 1-6 to execute)</span></div>
      <table class="term-ascii-table">
        <tr><th>Track</th><th>SQL Statement</th></tr>
        ${rowsHtml}
      </table>
    `;
    terminalOutput.appendChild(box);
  }
  function printStatus() {
    const box = document.createElement("div");
    box.className = "term-report-box";
    box.innerHTML = `
      <div class="term-report-title"><span>SYSTEM CONSOLE TELEMETRY</span></div>
      <table class="term-ascii-table">
        <tr><td>Isolation Level:</td><td><code>REPEATABLE READ (Snapshot Isolation)</code></td></tr>
        <tr><td>Rollback Interlock:</td><td><code>ENFORCED (finally block guarantee)</code></td></tr>
        <tr><td>Real Database State:</td><td><code>PRISTINE (0 bytes committed to storage)</code></td></tr>
        <tr><td>Catalog Tracing:</td><td><code>pg_depend, pg_rewrite, pg_constraint</code></td></tr>
      </table>
    `;
    terminalOutput.appendChild(box);
  }
  async function runSimulationRequest(sql) {
    try {
      const response = await fetch("/api/whatif", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql })
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const report = await response.json();
      appendTerminalLogs(report.logs || []);
      appendTerminalReportBox(report);
      renderDashboard(report);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);
      const errDiv = document.createElement("div");
      errDiv.style.color = "var(--c-crimson)";
      errDiv.style.fontSize = "0.75rem";
      errDiv.style.margin = "4px 0 4px 12px";
      errDiv.textContent = `[ERROR] Console communication failure: ${errMsg}`;
      terminalOutput.appendChild(errDiv);
    }
    scrollTerminalToBottom();
    queryInput.focus();
  }
  function appendTerminalLogs(logs) {
    const logBox = document.createElement("div");
    logBox.style.margin = "4px 0";
    logs.forEach((log) => {
      const p = document.createElement("div");
      p.style.fontSize = "0.74rem";
      p.style.marginLeft = "12px";
      p.style.lineHeight = "1.5";
      if (log.includes("[ERROR]") || log.includes("[REJECT]"))
        p.style.color = "var(--c-crimson)";
      else if (log.includes("[CONFIRM]") || log.includes("[STATUS]"))
        p.style.color = "var(--c-mint)";
      else if (log.includes("[CATALOG]"))
        p.style.color = "var(--c-gold)";
      else if (log.includes("[ROLLBACK]"))
        p.style.color = "var(--c-rose)";
      else if (log.includes("[SNAPSHOT]") || log.includes("[EXECUTE]"))
        p.style.color = "var(--c-cyan)";
      else
        p.style.color = "rgba(247, 247, 234, 0.7)";
      p.textContent = log;
      logBox.appendChild(p);
    });
    terminalOutput.appendChild(logBox);
  }
  function appendTerminalReportBox(report) {
    const box = document.createElement("div");
    box.className = `term-report-box ${report.status === "ERROR" ? "error" : ""}`;
    if (report.status === "ERROR") {
      box.innerHTML = `
        <div class="term-report-title"><span style="color:var(--c-crimson)">[REJECTED] SAFETY VIOLATION</span> <span>${report.execution_time_ms} ms</span></div>
        <p style="color:var(--c-crimson); margin-top:4px;">${escapeHtml(report.error_message || "Validation Error")}</p>
      `;
      terminalOutput.appendChild(box);
      return;
    }
    let tablesHtml = "";
    (report.tables_affected || []).forEach((t) => {
      tablesHtml += `<tr><td>${escapeHtml(t.table)}</td><td>${escapeHtml(t.action || "MODIFIED")}</td><td>${t.rows_changed} rows</td></tr>`;
    });
    let metricsHtml = "";
    (report.metrics || []).forEach((m) => {
      const before = m.before !== undefined ? m.before + (m.unit || "") : "—";
      const after = m.after !== undefined ? m.after + (m.unit || "") : "—";
      const change = m.change !== undefined ? m.change : m.status || "—";
      metricsHtml += `<tr><td>${escapeHtml(m.metric)}</td><td>${escapeHtml(String(m.student_id || "—"))}</td><td>${before}</td><td>${after}</td><td><strong>${escapeHtml(String(change))}</strong></td></tr>`;
    });
    let brokenHtml = "";
    (report.broken_dependencies || []).forEach((b) => {
      brokenHtml += `<tr><td style="color:var(--c-crimson); font-weight:700">${escapeHtml(b.object_name)}</td><td>${escapeHtml(b.object_type)}</td><td>${escapeHtml(b.reason)}</td></tr>`;
    });
    let content = `
      <div class="term-report-title">
        <span>IMPACT TELEMETRY // [${escapeHtml(report.statement_type)}]</span>
        <span>${report.execution_time_ms} ms</span>
      </div>
    `;
    if (tablesHtml) {
      content += `
        <div style="color:var(--c-gold); font-size:0.7rem; font-weight:700; margin-top:6px;">RELATIONS MODIFIED IN SNAPSHOT:</div>
        <table class="term-ascii-table">
          <tr><th>Relation</th><th>Action</th><th>Delta</th></tr>
          ${tablesHtml}
        </table>
      `;
    }
    if (metricsHtml) {
      content += `
        <div style="color:var(--c-gold); font-size:0.7rem; font-weight:700; margin-top:6px;">DERIVED ACADEMIC METRICS:</div>
        <table class="term-ascii-table">
          <tr><th>Metric</th><th>Student</th><th>Baseline</th><th>Hypothetical</th><th>Delta</th></tr>
          ${metricsHtml}
        </table>
      `;
    }
    if (brokenHtml) {
      content += `
        <div style="color:var(--c-crimson); font-size:0.7rem; font-weight:700; margin-top:6px;">TRIPPED DEPENDENCIES (CATALOG SCAN):</div>
        <table class="term-ascii-table">
          <tr><th>Object</th><th>Type</th><th>Impact</th></tr>
          ${brokenHtml}
        </table>
      `;
    }
    content += `<div class="term-integrity-badge">INTERLOCK ACTIVE: PostgreSQL ROLLBACK executed. Live database pristine.</div>`;
    box.innerHTML = content;
    terminalOutput.appendChild(box);
  }
  function scrollTerminalToBottom() {
    terminalScreen.scrollTop = terminalScreen.scrollHeight;
  }
  function renderDashboard(report) {
    metaSql.textContent = report.statement;
    metaType.textContent = report.statement_type || "UNKNOWN";
    metaTime.textContent = `${report.execution_time_ms || 0} ms`;
    if (report.status === "ERROR") {
      reportStatusBadge.className = "tally-pill pill-rejected";
      reportStatusBadge.textContent = "TRIPPED";
      metaMode.textContent = "HALTED (SAFETY INTERLOCK)";
      metaMode.style.color = "var(--c-crimson)";
    } else if (report.status === "VERIFIED_PRISTINE") {
      reportStatusBadge.className = "tally-pill pill-verified";
      reportStatusBadge.textContent = "VERIFIED";
      metaMode.textContent = "DIRECT READ ONLY";
      metaMode.style.color = "var(--c-mint)";
    } else {
      reportStatusBadge.className = "tally-pill pill-simulated";
      reportStatusBadge.textContent = "SIMULATED";
      metaMode.textContent = "REPEATABLE READ (ROLLED BACK)";
      metaMode.style.color = "var(--c-mint)";
    }
    renderTablesAffected(report.tables_affected || []);
    if (report.statement_type === "DDL_SCHEMA_CHANGE") {
      metricsSection.style.display = "none";
      schemaSection.style.display = "block";
      renderSchemaDependencies(report.broken_dependencies || []);
    } else {
      metricsSection.style.display = "flex";
      schemaSection.style.display = "none";
      renderMetrics(report.metrics || [], report.status);
    }
  }
  function renderTablesAffected(tables) {
    tablesAffectedList.innerHTML = "";
    if (tables.length === 0) {
      tablesAffectedList.innerHTML = `<div class="ledger-empty">Zero physical rows modified in database storage.</div>`;
      totalRowsBadge.textContent = "0 ROWS";
      return;
    }
    let totalRows = 0;
    tables.forEach((t) => {
      totalRows += t.rows_changed || 0;
      const row = document.createElement("div");
      row.className = "ledger-row-item";
      let actionClass = "deleted";
      if (t.action && t.action.includes("CASCADE"))
        actionClass = "cascade";
      else if (t.action && t.action.includes("UPDATE"))
        actionClass = "updated";
      row.innerHTML = `
        <span class="ledger-tbl-name">${escapeHtml(t.table)}</span>
        <div class="ledger-tags">
          <span class="action-tag ${actionClass}">${escapeHtml(t.action || "MODIFIED")}</span>
          <span>${t.rows_changed || 0} rows</span>
        </div>
      `;
      tablesAffectedList.appendChild(row);
    });
    totalRowsBadge.textContent = `${totalRows} ROWS`;
  }
  function renderMetrics(metrics, status) {
    attBefore.textContent = "—";
    attAfter.textContent = "—";
    attendanceDeltaBadge.textContent = "0.0%";
    attendanceDeltaBadge.className = "delta-tag neutral";
    attendanceBar.style.width = "0%";
    attendanceBar.className = "vu-led-segments";
    eligBefore.textContent = "—";
    eligBefore.className = "gate-tally neutral";
    eligAfter.textContent = "—";
    eligAfter.className = "gate-tally neutral";
    eligReason.textContent = "Evaluated against VIT 75% attendance rule.";
    eligibilityStatusBadge.textContent = "—";
    eligibilityStatusBadge.className = "status-tally-pill neutral";
    cgpaBefore.textContent = "—";
    cgpaAfter.textContent = "—";
    cgpaDeltaBadge.textContent = "0.00";
    cgpaDeltaBadge.className = "delta-tag neutral";
    cgpaNote.textContent = "Calculated across active course credit weights in marks table.";
    if (status === "VERIFIED_PRISTINE") {
      const live = metrics.find((m) => m.metric === "live_data_state");
      if (live && live.current_attendance_pct !== undefined && live.current_cgpa !== undefined) {
        attBefore.textContent = `${live.current_attendance_pct}%`;
        attAfter.textContent = `${live.current_attendance_pct}%`;
        attendanceDeltaBadge.textContent = "LIVE DATA";
        attendanceDeltaBadge.className = "delta-tag positive";
        attendanceBar.style.width = `${Math.min(live.current_attendance_pct, 100)}%`;
        eligBefore.textContent = live.exam_eligibility || "ELIGIBLE";
        eligBefore.className = "gate-tally eligible";
        eligAfter.textContent = live.exam_eligibility || "ELIGIBLE";
        eligAfter.className = "gate-tally eligible";
        eligReason.textContent = "Direct audit of live PostgreSQL storage. Pristine.";
        cgpaBefore.textContent = live.current_cgpa.toFixed(2);
        cgpaAfter.textContent = live.current_cgpa.toFixed(2);
        cgpaDeltaBadge.textContent = "PRISTINE";
        cgpaDeltaBadge.className = "delta-tag positive";
        cgpaNote.textContent = `Student: ${live.student_name} (ID: ${live.student_id})`;
      }
      return;
    }
    metrics.forEach((m) => {
      if (m.metric === "attendance_percentage") {
        const b = typeof m.before === "number" ? m.before.toFixed(1) : String(m.before || "—");
        const a = typeof m.after === "number" ? m.after.toFixed(1) : String(m.after || "—");
        attBefore.textContent = `${b}%`;
        attAfter.textContent = `${a}%`;
        if (typeof m.change === "number") {
          const changeVal = m.change.toFixed(1);
          attendanceDeltaBadge.textContent = `${m.change > 0 ? "+" : ""}${changeVal}%`;
          if (m.change < 0)
            attendanceDeltaBadge.className = "delta-tag negative";
          else if (m.change > 0)
            attendanceDeltaBadge.className = "delta-tag positive";
        }
        if (typeof m.after === "number") {
          attendanceBar.style.width = `${Math.min(m.after, 100)}%`;
          if (m.after < 75) {
            attendanceBar.className = "vu-led-segments danger";
          } else {
            attendanceBar.className = "vu-led-segments";
          }
        }
      }
      if (m.metric === "exam_eligibility") {
        eligBefore.textContent = String(m.before || "—");
        eligBefore.className = `gate-tally ${m.before === "ELIGIBLE" ? "eligible" : "ineligible"}`;
        eligAfter.textContent = String(m.after || "—");
        eligAfter.className = `gate-tally ${m.after === "ELIGIBLE" ? "eligible" : "ineligible"}`;
        eligReason.textContent = m.reason || (m.change === "FLIPPED_TO_NO" ? "Attendance fell below 75% requirement." : "Eligibility unchanged.");
        eligibilityStatusBadge.textContent = m.change === "FLIPPED_TO_NO" ? "FLIPPED TO NO" : "UNCHANGED";
        eligibilityStatusBadge.className = m.change === "FLIPPED_TO_NO" ? "status-tally-pill warn" : "status-tally-pill neutral";
      }
      if (m.metric === "cgpa") {
        const b = typeof m.before === "number" ? m.before.toFixed(2) : String(m.before || "—");
        const a = typeof m.after === "number" ? m.after.toFixed(2) : String(m.after || "—");
        cgpaBefore.textContent = b;
        cgpaAfter.textContent = a;
        if (typeof m.change === "number") {
          const changeVal = m.change.toFixed(2);
          cgpaDeltaBadge.textContent = `${m.change > 0 ? "+" : ""}${changeVal}`;
          if (m.change < 0)
            cgpaDeltaBadge.className = "delta-tag negative";
          else if (m.change > 0)
            cgpaDeltaBadge.className = "delta-tag positive";
        }
        if (m.reason)
          cgpaNote.textContent = m.reason;
      }
    });
  }
  function renderSchemaDependencies(deps) {
    brokenDependenciesList.innerHTML = "";
    brokenCountBadge.textContent = `${deps.length} FAULTS`;
    if (deps.length === 0) {
      brokenDependenciesList.innerHTML = `<div class="ledger-empty">Zero reverse dependency faults detected in catalogs.</div>`;
      return;
    }
    deps.forEach((d) => {
      const item = document.createElement("div");
      item.className = "fault-row-item";
      item.innerHTML = `
        <div>
          <span class="fault-name">${escapeHtml(d.object_name)}</span>
          <span class="fault-type">[${escapeHtml(d.object_type)}]</span>
        </div>
        <div class="fault-reason">${escapeHtml(d.reason)}</div>
      `;
      brokenDependenciesList.appendChild(item);
    });
  }
  function escapeHtml(str) {
    if (!str)
      return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
});
