/**
 * Workspace Service — API client for workspace file explorer, test reports, quality gates, and snapshot rollbacks.
 */

import api from "@/lib/api";

export interface WorkspaceFile {
  id: string;
  session_id: string;
  file_path: string;
  content: string;
  language: string;
  version: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TestReport {
  id: string;
  workflow_id: string;
  project_type: string;
  test_command: string;
  passed: boolean;
  execution_time: number;
  stdout: string;
  stderr: string;
  bug_report: {
    failed_file?: string;
    failed_test?: string;
    stack_trace?: string;
    suggested_fix?: string;
    severity?: string;
  };
  created_at: string;
}

export interface QualityReport {
  id: string;
  workflow_id: string;
  quality_gate: "PASS" | "PASS_WITH_WARNINGS" | "FAIL";
  overall_score: number;
  lint_findings: Array<Record<string, unknown>>;
  security_findings: Array<Record<string, unknown>>;
  created_at: string;
}

export interface QualitySummary {
  total_reviews: number;
  pass_count: number;
  pass_with_warnings_count: number;
  fail_count: number;
  pass_rate_percentage: number;
}

/**
 * List workspace files.
 * GET /api/workspace
 */
export async function fetchWorkspaceFiles(): Promise<WorkspaceFile[]> {
  const { data } = await api.get<WorkspaceFile[]>("/api/workspace");
  return data;
}

/**
 * Read file content.
 * GET /api/workspace/files
 */
export async function fetchWorkspaceFileContent(path: string): Promise<{ path: string; content: string }> {
  const { data } = await api.get<{ path: string; content: string }>("/api/workspace/files", {
    params: { path },
  });
  return data;
}

/**
 * Rollback workspace to snapshot.
 * POST /api/workspace/rollback
 */
export async function rollbackWorkspace(snapshotId: string): Promise<{ status: string; message: string }> {
  const { data } = await api.post<{ status: string; message: string }>("/api/workspace/rollback", {
    snapshot_id: snapshotId,
  });
  return data;
}

/**
 * Fetch test execution reports.
 * GET /api/tests
 */
export async function fetchTestReports(): Promise<TestReport[]> {
  const { data } = await api.get<TestReport[]>("/api/tests");
  return data;
}

/**
 * Fetch quality reports.
 * GET /api/reviews
 */
export async function fetchQualityReports(): Promise<QualityReport[]> {
  const { data } = await api.get<QualityReport[]>("/api/reviews");
  return data;
}

/**
 * Fetch quality gate metrics summary.
 * GET /api/quality
 */
export async function fetchQualitySummary(): Promise<QualitySummary> {
  const { data } = await api.get<QualitySummary>("/api/quality");
  return data;
}
