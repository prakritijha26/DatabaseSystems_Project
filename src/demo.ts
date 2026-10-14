/**
 * src/demo.ts
 * Automated evaluation runner for the 6 core review scenarios in TypeScript.
 * Part C Deliverable: Scripted demonstration of What-If Database for examiner/viva presentation.
 *
 * Usage:
 *   bun run src/demo.ts
 *   bun run demo
 *   bun run demo --interactive   # Pause and wait for [Enter] between scenarios
 */

import { executeQuery, formatReport, C } from "./cli";
import * as readline from "readline";

interface DemoScenario {
  number: number;
  title: string;
  description: string;
  sql: string;
}

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    number: 1,
    title: "Attendance Deletion causing Eligibility Flip",
    description: "Simulates deleting 14 attendance records for student 1042. Recomputed attendance falls below VIT's 75% threshold, flipping exam status from ELIGIBLE to INELIGIBLE.",
    sql: "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;"
  },
  {
    number: 2,
    title: "Mark Update causing CGPA Recalculation",
    description: "Simulates adjusting student 1042's CSE202 score. The credit-weighted CGPA view re-evaluates inside snapshot isolation and reports the exact numerical delta.",
    sql: "WHAT_IF UPDATE marks SET score = 45 WHERE student_id = 1042 AND course_id = 'CSE202';"
  },
  {
    number: 3,
    title: "Course Deregistration with Cascades (ON DELETE CASCADE)",
    description: "Simulates removing a student from a course enrollment. Foreign key cascades automatically delete linked marks and attendance entries in the transaction snapshot.",
    sql: "WHAT_IF DELETE FROM enrollments WHERE student_id = 1042 AND course_id = 'CSE202';"
  },
  {
    number: 4,
    title: "Hypothetical DDL with Schema Catalog Tracing (DROP COLUMN)",
    description: "Simulates dropping column 'score' from table 'marks'. Queries pg_depend and pg_rewrite to list the broken views, triggers, and failing metric queries.",
    sql: "WHAT_IF ALTER TABLE marks DROP COLUMN score;"
  },
  {
    number: 5,
    title: "Sandbox Security Violation (Attempted COMMIT Injection)",
    description: "Simulates an adversarial attempt to commit a transaction or escape the sandbox. The AST validator intercepts and rejects the statement before snapshot acquisition.",
    sql: "WHAT_IF COMMIT;"
  },
  {
    number: 6,
    title: "Post-Simulation Immutability Verification (Plain SELECT)",
    description: "Shows the verification fixture offline; the current live DML engine rejects SELECT.",
    sql: "SELECT student_id, name, attendance_pct, cgpa, exam_eligible FROM student_summary_view WHERE student_id = 1042;"
  }
];

function waitForKey(prompt: string): Promise<void> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  return new Promise(resolve => {
    rl.question(prompt, () => {
      rl.close();
      resolve();
    });
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function runDemo(interactive = false): Promise<void> {
  console.log(`\n${C.BOLD}${C.CYAN}${"=".repeat(76)}${C.RESET}`);
  console.log(`${C.BOLD}${C.CYAN}   WHAT-IF DATABASE: AUTOMATED DEMO & EVALUATION SUITE [TYPESCRIPT]${C.RESET}`);
  console.log(`${C.CYAN}   Course: BACSE202 (DBMS) | Snapshot Isolation: REPEATABLE READ${C.RESET}`);
  console.log(`${C.CYAN}   Runtime: Bun + TypeScript Native Driver${C.RESET}`);
  console.log(`${C.BOLD}${C.CYAN}${"=".repeat(76)}${C.RESET}\n`);

  for (const sc of DEMO_SCENARIOS) {
    console.log(`\n${C.BOLD}${C.GOLD}${"=".repeat(76)}${C.RESET}`);
    console.log(`${C.BOLD}${C.GOLD} [SCENARIO ${sc.number}/6] ${sc.title.toUpperCase()}${C.RESET}`);
    console.log(`${C.BOLD}${C.GOLD}${"=".repeat(76)}${C.RESET}`);
    console.log(`${C.BOLD}Scenario Goal:${C.RESET} ${sc.description}`);
    console.log(`${C.BOLD}Input Query:${C.RESET}   ${C.CYAN}${sc.sql}${C.RESET}`);

    if (interactive) {
      await waitForKey(`\n${C.DIM}Press [Enter] to simulate this scenario...${C.RESET}`);
    } else {
      await sleep(300);
    }

    try {
      const report = await executeQuery(sc.sql);
      formatReport(report);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`${C.CRIMSON}[ERROR] Failed to run scenario ${sc.number}: ${msg}${C.RESET}`);
    }
  }

  console.log(`\n${C.BOLD}${C.MINT}${"=".repeat(76)}${C.RESET}`);
  console.log(`${C.BOLD}${C.MINT}   ✅ DEMO RUN COMPLETE — REVIEW THE SIX REPORTS.${C.RESET}`);
  console.log(`${C.MINT}   Review each report for backend mode, errors, and rollback confirmation.${C.RESET}`);
  console.log(`${C.BOLD}${C.MINT}${"=".repeat(76)}${C.RESET}\n`);
}

async function main() {
  const isInteractive = process.argv.includes("--interactive") || process.argv.includes("-i");
  await runDemo(isInteractive);
}

if (import.meta.main) {
  main();
}
