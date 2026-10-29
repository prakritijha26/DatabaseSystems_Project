/**
 * src/cli.ts
 * Native TypeScript Command Line Interface for What-If Database.
 * Runs directly with Bun: bun run src/cli.ts [query]
 */

import type { ImpactReport } from "./types";
import { createInterface } from "node:readline";

// Lospec Revival Palette (24-bit Truecolor ANSI)
export const C = {
  CREAM: "\x1b[38;2;247;247;234m",
  DENIM: "\x1b[38;2;71;118;195m",
  CYAN: "\x1b[38;2;47;201;237m",
  MINT: "\x1b[38;2;170;239;213m",
  GOLD: "\x1b[38;2;245;226;145m",
  ROSE: "\x1b[38;2;242;156;172m",
  CRIMSON: "\x1b[38;2;245;85;74m",
  DIM: "\x1b[38;2;150;140;170m",
  BOLD: "\x1b[1m",
  RESET: "\x1b[0m"
};

export async function executeQuery(sql: string): Promise<ImpactReport> {
  const permanent = /^\s*(?:APPLY\s+|(?:RESEED|RESET)\s*;?\s*$)/i.test(sql);
  // Permanent commands are never replayed after an ambiguous HTTP result.
  try {
    const res = await fetch(process.env.WHATIF_API_URL ?? "http://127.0.0.1:8000/api/whatif", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql }),
      signal: AbortSignal.timeout(15000)
    });
    if (res.ok) {
      const report = (await res.json()) as ImpactReport;
      if (process.env.WHATIF_REQUIRE_LIVE === "1" && report.engine_backend !== "live") throw new Error("Live mode requires PostgreSQL.");
      return report;
    }
    throw new Error(`Backend returned HTTP ${res.status}.`);
  } catch (error) {
    const refused = (error as { code?: string })?.code === "ECONNREFUSED" ||
      (error as { cause?: { code?: string } })?.cause?.code === "ECONNREFUSED";
    if (permanent && !refused) throw new Error("Permanent command was not retried: server outcome may be unknown. Read back the data before retrying.");
    // A refused connection was never delivered; otherwise only read/simulation requests may fall back.
  }

  const proc = Bun.spawn([
    process.env.WHATIF_PYTHON ?? "python3",
    "-c",
    `
import json, sys
from app import run_whatif
report = run_whatif(sys.argv[1])
print(json.dumps(report))
`,
    sql
  ]);

  const outputText = await new Response(proc.stdout).text();
  if (await proc.exited !== 0) throw new Error("Python engine subprocess failed.");
  try {
    return JSON.parse(outputText.trim()) as ImpactReport;
  } catch (err) {
    throw new Error(`Failed to parse engine output: ${outputText}`);
  }
}

export function formatReport(report: ImpactReport, showJson = false): void {
  if (showJson) {
    console.log(JSON.stringify(report, null, 2));
    return;
  }

  console.log(`\n${C.BOLD}┌── SIMULATION TELEMETRY // [${report.statement_type}] ─────────────────────────────────${C.RESET}`);
  console.log(`│ ${C.BOLD}SQL Statement:${C.RESET}    ${report.statement}`);
  console.log(`│ ${C.BOLD}Engine Status:${C.RESET}    ${report.status === "ERROR" ? C.CRIMSON + "[TRIPPED / REJECTED]" : report.engine_backend === "mock" ? C.GOLD + "[OFFLINE FIXTURE]" : report.status === "COMMITTED" && report.committed ? C.GOLD + "[COMMITTED / PERMANENT]" : C.MINT + "[SIMULATED / SNAPSHOT]"} ${C.RESET}`);
  console.log(`│ ${C.BOLD}Execution Time:${C.RESET}   ${report.execution_time_ms.toFixed(2)} ms`);
  console.log(`└──${"─".repeat(70)}`);

  if (report.logs && report.logs.length > 0) {
    console.log(`\n${C.DIM}Console Trace Stream:${C.RESET}`);
    for (const log of report.logs) {
      if (log.includes("[ERROR]") || log.includes("[REJECT]")) {
        console.log(`  ${C.CRIMSON}${log}${C.RESET}`);
      } else if (log.includes("[CONFIRM]") || log.includes("[STATUS]")) {
        console.log(`  ${C.MINT}${log}${C.RESET}`);
      } else if (log.includes("[ROLLBACK]")) {
        console.log(`  ${C.ROSE}${log}${C.RESET}`);
      } else {
        console.log(`  ${C.DIM}${log}${C.RESET}`);
      }
    }
  }

  if (report.status === "ERROR") {
    console.log(`\n${C.CRIMSON}❌ Error:${C.RESET} ${report.error_message || "Validation error"}\n`);
    return;
  }

  if (report.query_columns) {
    console.log(`\n${C.GOLD}Read-only SELECT result:${C.RESET}`);
    const rows = (report.query_rows ?? []).map(row => row.map(value => value === null ? "NULL" : String(value)));
    const widths = report.query_columns.map((column, i) => Math.max(column.length, ...rows.map(row => (row[i] ?? "").length)));
    console.log(report.query_columns.map((column, i) => column.padEnd(widths[i])).join(" | "));
    console.log(widths.map(width => "-".repeat(width)).join("-+-"));
    for (const row of rows) console.log(row.map((value, i) => value.padEnd(widths[i])).join(" | "));
    console.log(`${rows.length} row(s)${report.query_truncated ? " (truncated)" : ""}`);
  }

  // Relations modified
  const tables = report.tables_affected || [];
  console.log(`\n${C.GOLD}${C.BOLD}Relations Modified in Snapshot:${C.RESET}`);
  if (tables.length === 0) {
    console.log(`  ${C.DIM}(No changed relations reported)${C.RESET}`);
  } else {
    console.log(`  ${C.BOLD}${"Relation".padEnd(22)} ${"Action".padEnd(22)} ${"Delta".padEnd(12)}${C.RESET}`);
    console.log(`  ${"-".repeat(22)} ${"-".repeat(22)} ${"-".repeat(12)}`);
    for (const t of tables) {
      const actColor = t.action?.includes("CASCADE") ? C.ROSE : (t.action?.includes("DELETE") ? C.CRIMSON : C.CYAN);
      console.log(`  ${t.table.padEnd(22)} ${actColor}${(t.action || "MODIFIED").padEnd(22)}${C.RESET} ${String(t.rows_changed).padEnd(12)}`);
    }
  }

  // Metrics
  const metrics = report.metrics || [];
  if (metrics.length > 0) {
    console.log(`\n${C.GOLD}${C.BOLD}Derived Academic Metrics (VU Telemetry):${C.RESET}`);
    console.log(`  ${C.BOLD}${"Metric".padEnd(26)} ${"Student".padEnd(12)} ${"Baseline".padEnd(14)} ${"Hypothetical".padEnd(16)} ${"Delta".padEnd(16)}${C.RESET}`);
    console.log(`  ${"-".repeat(26)} ${"-".repeat(12)} ${"-".repeat(14)} ${"-".repeat(16)} ${"-".repeat(16)}`);
    for (const m of metrics) {
      const unit = m.unit || "";
      const before = m.before !== undefined ? `${m.before}${unit}` : "—";
      const after = m.after !== undefined ? `${m.after}${unit}` : "—";
      const change = m.change !== undefined ? String(m.change) : "—";
      const cColor = typeof m.change === "number" && m.change < 0 ? C.CRIMSON : (typeof m.change === "number" && m.change > 0 ? C.MINT : C.DIM);
      console.log(`  ${m.metric.padEnd(26)} ${String(m.student_id || "—").padEnd(12)} ${before.padEnd(14)} ${after.padEnd(16)} ${cColor}${change.padEnd(16)}${C.RESET}`);
    }
  }

  // Tripped dependencies
  const broken = report.broken_dependencies || [];
  if (broken.length > 0) {
    console.log(`\n${C.CRIMSON}${C.BOLD}Tripped Catalog Reverse Dependencies:${C.RESET}`);
    console.log(`  ${C.BOLD}${"Object Name".padEnd(28)} ${"Type".padEnd(16)} ${"Impact Detail".padEnd(35)}${C.RESET}`);
    console.log(`  ${"-".repeat(28)} ${"-".repeat(16)} ${"-".repeat(35)}`);
    for (const b of broken) {
      console.log(`  ${C.CRIMSON}${b.object_name.padEnd(28)}${C.RESET} ${b.object_type.padEnd(16)} ${C.DIM}${b.reason.padEnd(35)}${C.RESET}`);
    }
  }

  const interlock = report.engine_backend === "mock" ? "Offline fixture: no SQL executed." : report.status === "COMMITTED" && report.committed ? "Permanent commit confirmed by PostgreSQL. Data updated on disk." : report.rolled_back ? "Transaction rollback confirmed." : "Rollback not confirmed.";
  console.log(`\n${report.committed ? C.GOLD : C.MINT}INTERLOCK:${C.RESET} ${interlock}\n`);
}

async function main() {
  const args = process.argv.slice(2);
  const showJson = args.includes("--json");
  const queryArgs = args.filter(a => a !== "--json");

  if (queryArgs.length === 0) {
    console.log(`${C.CYAN}${C.BOLD}WHAT-IF DATABASE // INTERACTIVE REPL${C.RESET}`);
    console.log("WHAT_IF simulates; APPLY permanently commits; RESEED/RESET restores sample data. Each line executes one query.");
    console.log("Type 'exit', 'quit', or '\\q' to exit. Up/Down recalls command history.");
    const terminal = Boolean(process.stdin.isTTY && process.stdout.isTTY);
    const rl = createInterface({ input: process.stdin, output: process.stdout, terminal, removeHistoryDuplicates: true });
    let closed = false;
    rl.on('close', () => { closed = true; });
    rl.setPrompt('whatif> ');
    if (terminal) rl.prompt();
    else process.stdout.write('whatif> ');
    try {
      for await (const line of rl) {
        const sql = line.trim();
        if (['exit', 'quit', '\\q'].includes(sql.toLowerCase())) break;
        if (sql) {
          try {
            formatReport(await executeQuery(sql), showJson);
          } catch (err: unknown) {
            console.error(`${C.CRIMSON}[ERROR] ${err instanceof Error ? err.message : String(err)}${C.RESET}`);
          }
        }
        if (terminal && !closed) rl.prompt();
        else if (!terminal) process.stdout.write('whatif> ');
      }
    } finally {
      rl.close();
    }
    return;
  }

  const sql = queryArgs.join(" ");
  try {
    const report = await executeQuery(sql);
    formatReport(report, showJson);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`${C.CRIMSON}[ERROR] ${msg}${C.RESET}`);
  }
}

if (import.meta.main) {
  main();
}
