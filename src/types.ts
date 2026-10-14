/**
 * src/types.ts
 * Core TypeScript type definitions for What-If Database.
 * Defines the agreed ImpactReport interface contract between frontend and simulation engines.
 */

export type StatementType = 
  | "DML"
  | "DDL_SCHEMA_CHANGE"
  | "VERIFICATION_SELECT"
  | "REJECTED"
  | "UNKNOWN";

export type SimulationStatus = 
  | "SIMULATED"
  | "VERIFIED_PRISTINE"
  | "ERROR";

export interface TableAffected {
  table: string;
  rows_changed: number;
  action?: "DELETED" | "UPDATED" | "PRIMARY_DELETE" | "ON_DELETE_CASCADE" | "COLUMN_DROPPED (hypothetical)" | string;
}

export interface MetricItem {
  metric: string;
  student_id?: number | string;
  student_name?: string;
  course_code?: string;
  before?: number | string;
  after?: number | string;
  change?: number | string;
  threshold?: number;
  unit?: string;
  reason?: string;
  status?: string;
  current_attendance_pct?: number;
  current_cgpa?: number;
  exam_eligibility?: "ELIGIBLE" | "INELIGIBLE";
}

export interface BrokenDependency {
  object_name: string;
  object_type: "VIEW" | "TRIGGER" | "CONSTRAINT" | "METRIC_QUERY" | string;
  reason: string;
  severity?: "CRITICAL_BREAK" | "TRIGGER_INVALIDATED" | "EXECUTION_FAILURE" | string;
}

export interface ImpactReport {
  statement: string;
  statement_type: StatementType;
  status: SimulationStatus;
  execution_time_ms: number;
  error_message?: string;
  tables_affected: TableAffected[];
  metrics: MetricItem[];
  broken_dependencies: BrokenDependency[];
  logs: string[];
  engine_backend?: string;
  rolled_back?: boolean;
}

export interface ReviewTrackScenario {
  number: number;
  id: string;
  title: string;
  sql: string;
  hint: string;
}
