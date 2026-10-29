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

import scenarios from '../scenarios.json';
const DEMO_SCENARIOS: DemoScenario[] = scenarios;

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

  let failures = 0;
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
      if ((sc.number === 5 ? report.status !== "ERROR" : report.status === "ERROR") || (process.env.WHATIF_REQUIRE_LIVE === "1" && report.engine_backend !== "live")) failures++;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      failures++;
      console.error(`${C.CRIMSON}[ERROR] Failed to run scenario ${sc.number}: ${msg}${C.RESET}`);
    }
  }

  if (failures) throw new Error(`${failures} review scenarios failed expectations.`);
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
