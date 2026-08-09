/**
 * /app/workspace — Canonical Autonomous Workspace Studio route inside the /app/* application shell.
 *
 * Features:
 * - Project File Explorer & Syntax Code Viewer
 * - Version History & Snapshot Rollback Engine
 * - Test Suite Reports & Stack Trace Inspector
 * - Quality Gate & Static Security Analysis (Ruff + Bandit)
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Folder,
  FileCode,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Bug,
  RefreshCw,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchWorkspaceFiles,
  fetchWorkspaceFileContent,
  fetchTestReports,
  fetchQualityReports,
  fetchQualitySummary,
  type WorkspaceFile,
  type TestReport,
  type QualityReport,
  type QualitySummary,
} from "@/services/workspace-service";

type ActiveTab = "files" | "tests" | "quality";

export default function WorkspacePage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("files");
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<WorkspaceFile | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [testReports, setTestReports] = useState<TestReport[]>([]);
  const [qualityReports, setQualityReports] = useState<QualityReport[]>([]);
  const [qualitySummary, setQualitySummary] = useState<QualitySummary | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [fileList, tests, reviews, qSummary] = await Promise.all([
        fetchWorkspaceFiles(),
        fetchTestReports(),
        fetchQualityReports(),
        fetchQualitySummary(),
      ]);
      setFiles(fileList);
      setTestReports(tests);
      setQualityReports(reviews);
      setQualitySummary(qSummary);

      if (fileList.length > 0 && !selectedFile) {
        setSelectedFile(fileList[0]);
        setFileContent(fileList[0].content);
      }
    } catch (err) {
      console.error("Failed to load workspace data:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedFile]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const selectFileItem = async (f: WorkspaceFile) => {
    setSelectedFile(f);
    try {
      const res = await fetchWorkspaceFileContent(f.file_path);
      setFileContent(res.content);
    } catch {
      setFileContent(f.content);
    }
  };

  const getGateBadge = (gate: string) => {
    switch (gate) {
      case "PASS":
        return (
          <span className="px-2 py-0.5 text-[9px] font-bold uppercase border text-[var(--accent-success)] border-[var(--accent-success)]">
            ✓ PASS
          </span>
        );
      case "PASS_WITH_WARNINGS":
        return (
          <span className="px-2 py-0.5 text-[9px] font-bold uppercase border text-[var(--accent-warning)] border-[var(--accent-warning)]">
            ⚠ WARNINGS
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[9px] font-bold uppercase border text-[var(--accent-error)] border-[var(--accent-error)]">
            ✕ FAIL
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Card */}
      <div className="p-6 brutalist-card flex flex-col sm:flex-row sm:items-center justify-between gap-4" style={{ background: "var(--bg-surface)" }}>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Folder className="w-5 h-5 text-[var(--accent-secondary)]" />
            <h1 className="text-h1 font-black tracking-tight uppercase" style={{ color: "var(--fg-primary)" }}>
              Autonomous Workspace Studio
            </h1>
          </div>
          <p className="text-body-sm text-[var(--fg-secondary)]">
            Code sandbox explorer • Pytest test reports • Static quality gate &amp; security linters
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => loadData()}
            size="sm"
            className="brutalist-btn brutalist-btn-secondary text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Refresh Workspace
          </Button>

          <Link href="/app">
            <Button size="sm" className="brutalist-btn brutalist-btn-primary text-xs">
              <ArrowLeft className="w-3.5 h-3.5 mr-1" />
              Command Center
            </Button>
          </Link>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2">
        {[
          { id: "files", label: "Project Explorer", icon: FileCode },
          { id: "tests", label: "Test Suite Reports", icon: Bug },
          { id: "quality", label: "Quality Gate & Linters", icon: ShieldCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ActiveTab)}
              className={`brutalist-btn text-xs ${
                isActive
                  ? "brutalist-btn-primary"
                  : "brutalist-btn-secondary"
              }`}
            >
              <Icon className="w-3.5 h-3.5 mr-1 inline-block" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="text-caption text-[var(--fg-tertiary)] py-16 text-center">
          Loading workspace sandbox &amp; audit reports...
        </div>
      ) : (
        <>
          {/* Project Explorer Tab */}
          {activeTab === "files" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* File Tree List */}
              <div className="p-5 brutalist-card space-y-3" style={{ background: "var(--bg-surface)" }}>
                <h3 className="text-xs font-black uppercase text-[var(--fg-primary)] border-b-2 border-[var(--border-primary)] pb-2 flex items-center justify-between">
                  <span>Workspace Files</span>
                  <span className="text-[10px] text-[var(--fg-tertiary)] font-mono">{files.length} items</span>
                </h3>

                {files.length === 0 ? (
                  <div className="p-6 border-2 border-dashed border-[var(--border-secondary)] text-center text-caption text-[var(--fg-tertiary)]">
                    No project files found in workspace.
                  </div>
                ) : (
                  <div className="space-y-1.5 max-h-[550px] overflow-y-auto pr-1">
                    {files.map((f) => {
                      const isSelected = selectedFile?.id === f.id;
                      return (
                        <div
                          key={f.id}
                          onClick={() => selectFileItem(f)}
                          style={{
                            background: isSelected ? "var(--bg-secondary)" : "transparent",
                            borderColor: isSelected ? "var(--accent-primary)" : "var(--border-secondary)",
                          }}
                          className="p-2.5 border-2 cursor-pointer transition-all hover:border-[var(--border-primary)] flex items-center justify-between gap-2"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <FileCode className="w-4 h-4 text-[var(--accent-secondary)] shrink-0" />
                            <div className="min-w-0">
                              <div className="text-xs font-mono font-bold text-[var(--fg-primary)] truncate">
                                {f.file_path}
                              </div>
                              <div className="text-[9px] font-mono text-[var(--fg-tertiary)] uppercase">
                                v{f.version} • {f.language}
                              </div>
                            </div>
                          </div>
                          <ChevronRight className="w-3.5 h-3.5 text-[var(--fg-tertiary)] shrink-0" />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Code Viewer Panel */}
              <div className="lg:col-span-2 p-5 brutalist-card space-y-4" style={{ background: "var(--bg-surface)" }}>
                {selectedFile ? (
                  <>
                    <div className="flex items-center justify-between border-b-2 border-[var(--border-primary)] pb-3">
                      <div>
                        <h3 className="text-xs font-mono font-black uppercase text-[var(--fg-primary)]">
                          {selectedFile.file_path}
                        </h3>
                        <p className="text-[10px] font-mono text-[var(--fg-tertiary)] mt-0.5">
                          Language: {selectedFile.language} | Version: v{selectedFile.version}
                        </p>
                      </div>
                    </div>

                    <pre className="text-xs font-mono p-4 border-2 border-[var(--border-secondary)] bg-[var(--bg-primary)] overflow-x-auto max-h-[500px] text-[var(--fg-primary)] leading-relaxed">
                      {fileContent}
                    </pre>
                  </>
                ) : (
                  <div className="p-12 border-2 border-dashed border-[var(--border-secondary)] text-center text-caption text-[var(--fg-tertiary)]">
                    Select a file from the explorer to inspect syntax &amp; content.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Test Reports Tab */}
          {activeTab === "tests" && (
            <div className="p-5 brutalist-card space-y-4" style={{ background: "var(--bg-surface)" }}>
              <h3 className="text-xs font-black uppercase text-[var(--fg-primary)] border-b-2 border-[var(--border-primary)] pb-2 flex items-center gap-2">
                <Bug className="h-4 w-4 text-[var(--accent-secondary)]" />
                Pytest Execution Reports ({testReports.length})
              </h3>

              {testReports.length === 0 ? (
                <div className="p-8 border-2 border-dashed border-[var(--border-secondary)] text-center text-caption text-[var(--fg-tertiary)]">
                  No automated test reports generated yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b-2 border-[var(--border-primary)] text-[10px] font-black uppercase text-[var(--fg-tertiary)]">
                        <th className="p-2">Status</th>
                        <th className="p-2">Passed / Total</th>
                        <th className="p-2">Duration</th>
                        <th className="p-2">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-secondary)]">
                      {testReports.map((tr) => (
                        <tr key={tr.id} className="hover:bg-[var(--bg-secondary)] text-xs font-mono">
                          <td className="p-2 font-bold">
                            <span className={`px-1.5 py-0.5 text-[9px] uppercase border ${
                              tr.passed
                                ? "text-[var(--accent-success)] border-[var(--accent-success)]"
                                : "text-[var(--accent-error)] border-[var(--accent-error)]"
                            }`}>
                              {tr.passed ? "PASSED" : "FAILED"}
                            </span>
                          </td>
                          <td className="p-2 font-bold text-[var(--fg-primary)] truncate max-w-xs">
                            {tr.test_command || "pytest"}
                          </td>
                          <td className="p-2 text-[10px] text-[var(--fg-tertiary)]">
                            {tr.execution_time ? `${tr.execution_time.toFixed(2)}s` : "--"}
                          </td>
                          <td className="p-2 text-[10px] text-[var(--fg-tertiary)]">
                            {new Date(tr.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Quality Gate Tab */}
          {activeTab === "quality" && (
            <div className="p-5 brutalist-card space-y-6" style={{ background: "var(--bg-surface)" }}>
              {/* Summary Card */}
              {qualitySummary && (
                <div className="p-4 border-2 border-[var(--border-primary)] bg-[var(--bg-secondary)] flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-[var(--fg-tertiary)] block">PASS RATE</span>
                    <div className="mt-1 text-sm font-mono font-bold text-[var(--accent-success)]">{qualitySummary.pass_rate_percentage.toFixed(1)}% PASS</div>
                  </div>

                  <div className="flex gap-6 text-xs font-mono font-bold">
                    <div>
                      <span className="text-[10px] text-[var(--fg-tertiary)] uppercase block">TOTAL REVIEWS</span>
                      <span className="text-[var(--fg-primary)]">{qualitySummary.total_reviews}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[var(--fg-tertiary)] uppercase block">FAILED AUDITS</span>
                      <span className="text-[var(--accent-error)]">{qualitySummary.fail_count}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Quality Audit Table */}
              <div>
                <h3 className="text-xs font-black uppercase text-[var(--fg-primary)] border-b-2 border-[var(--border-primary)] pb-2 mb-4 flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-[var(--accent-success)]" />
                  Code Review &amp; Security Audits ({qualityReports.length})
                </h3>

                {qualityReports.length === 0 ? (
                  <div className="p-8 border-2 border-dashed border-[var(--border-secondary)] text-center text-caption text-[var(--fg-tertiary)]">
                    No quality gate audit reports found.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b-2 border-[var(--border-primary)] text-[10px] font-black uppercase text-[var(--fg-tertiary)]">
                          <th className="p-2">Gate Status</th>
                          <th className="p-2">Score</th>
                          <th className="p-2">Security Issues</th>
                          <th className="p-2">Reviewer Agent</th>
                          <th className="p-2">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-secondary)]">
                        {qualityReports.map((qr) => (
                          <tr key={qr.id} className="hover:bg-[var(--bg-secondary)] text-xs font-mono">
                            <td className="p-2 font-bold">{getGateBadge(qr.quality_gate)}</td>
                            <td className="p-2 font-bold text-[var(--fg-primary)]">{qr.overall_score}/100</td>
                            <td className="p-2 text-[10px] text-[var(--accent-warning)]">{(qr.security_findings?.length || 0) + (qr.lint_findings?.length || 0)} issues</td>
                            <td className="p-2 uppercase text-[10px] text-[var(--accent-secondary)]">Reviewer</td>
                            <td className="p-2 text-[10px] text-[var(--fg-tertiary)]">{new Date(qr.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
