/**
 * Autonomous Workspace Studio Page.
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
  RotateCcw,
  Bug,
  Terminal,
  RefreshCw,
  Loader2,
  ChevronRight,
  ShieldAlert,
  FileText,
  Clock,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchWorkspaceFiles,
  fetchWorkspaceFileContent,
  fetchTestReports,
  fetchQualityReports,
  fetchQualitySummary,
  rollbackWorkspace,
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
  const [actionLoading, setActionLoading] = useState(false);

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
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3.5 w-3.5" /> PASS
          </span>
        );
      case "PASS_WITH_WARNINGS":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <ShieldAlert className="h-3.5 w-3.5" /> PASS (WARNINGS)
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
            <XCircle className="h-3.5 w-3.5" /> FAIL
          </span>
        );
    }
  };

  return (
    <main className="flex-1 p-6 sm:p-8 lg:p-12 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors mb-3"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Folder className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Autonomous Workspace Studio</h1>
              <p className="text-sm text-zinc-400">
                File Sandbox • Pytest Runner • Static Analysis & Quality Gate
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={() => loadData()}
            variant="outline"
            size="sm"
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh Files
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2 mb-6 border-b border-zinc-800 pb-3">
        {[
          { id: "files", label: "Project Explorer", icon: FileCode },
          { id: "tests", label: "Test Reports", icon: Bug },
          { id: "quality", label: "Quality Gate & Linters", icon: ShieldCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ActiveTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800/40"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 text-indigo-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* Project Explorer Tab */}
          {activeTab === "files" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* File List */}
              <div className="space-y-3">
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                  Workspace Files ({files.length})
                </h2>

                {files.length === 0 ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-8 text-center backdrop-blur-sm">
                    <FileCode className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                    <p className="text-sm text-zinc-500">No project files created yet.</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                    {files.map((f) => {
                      const isSelected = selectedFile?.id === f.id;
                      return (
                        <div
                          key={f.id}
                          onClick={() => selectFileItem(f)}
                          className={`flex items-center justify-between p-3 rounded-lg border backdrop-blur-sm cursor-pointer transition-all ${
                            isSelected
                              ? "bg-zinc-800/80 border-indigo-500/40 ring-1 ring-indigo-500/30"
                              : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <FileCode className="h-4 w-4 text-indigo-400 shrink-0" />
                            <div>
                              <div className="text-xs font-mono font-semibold text-white">
                                {f.file_path}
                              </div>
                              <div className="text-[10px] text-zinc-500">
                                Version v{f.version} • {f.language}
                              </div>
                            </div>
                          </div>
                          <ChevronRight className="h-4 w-4 text-zinc-600" />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Code Inspector */}
              <div className="lg:col-span-2 space-y-4">
                {selectedFile ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                      <div>
                        <h3 className="text-sm font-bold text-white font-mono">{selectedFile.file_path}</h3>
                        <p className="text-[11px] text-zinc-400">Language: {selectedFile.language} | Version: v{selectedFile.version}</p>
                      </div>
                    </div>

                    <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 max-h-[500px] overflow-y-auto">
                      <pre className="text-xs font-mono text-zinc-200 whitespace-pre-wrap leading-relaxed">
                        {fileContent}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-12 text-center backdrop-blur-sm">
                    <FileText className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                    <p className="text-sm text-zinc-500">Select a file from the explorer to view source code.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Test Reports Tab */}
          {activeTab === "tests" && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                Automated Test Execution History ({testReports.length})
              </h2>

              {testReports.length === 0 ? (
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-12 text-center backdrop-blur-sm">
                  <Bug className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-500">No unit test execution reports recorded yet.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {testReports.map((t) => (
                    <div key={t.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-3">
                      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                        <div className="flex items-center gap-3">
                          {t.passed ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                              <CheckCircle2 className="h-3.5 w-3.5" /> PASSED
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-bold rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
                              <XCircle className="h-3.5 w-3.5" /> FAILED
                            </span>
                          )}
                          <span className="text-xs font-mono text-indigo-300">Cmd: {t.test_command}</span>
                        </div>
                        <span className="text-[11px] text-zinc-500">{t.execution_time}s duration</span>
                      </div>

                      {t.bug_report && t.bug_report.stack_trace && (
                        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 space-y-1">
                          <div className="text-xs font-bold text-red-300">Bug Report: {t.bug_report.failed_file}</div>
                          <div className="text-[11px] font-mono text-red-200/90 whitespace-pre-wrap max-h-36 overflow-y-auto">
                            {t.bug_report.stack_trace}
                          </div>
                        </div>
                      )}

                      <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 font-mono text-[11px] text-zinc-400 max-h-36 overflow-y-auto whitespace-pre-wrap">
                        {t.stdout || t.stderr || "No test output captured."}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Quality Gate Tab */}
          {activeTab === "quality" && (
            <div className="space-y-6">
              {/* Summary Metrics */}
              {qualitySummary && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                  <div className="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800 backdrop-blur-sm">
                    <div className="text-xs text-zinc-500 uppercase">Reviews Completed</div>
                    <div className="text-2xl font-bold text-white mt-1">{qualitySummary.total_reviews}</div>
                  </div>
                  <div className="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800 backdrop-blur-sm">
                    <div className="text-xs text-zinc-500 uppercase">Pass Rate</div>
                    <div className="text-2xl font-bold text-emerald-400 mt-1">{qualitySummary.pass_rate_percentage}%</div>
                  </div>
                  <div className="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800 backdrop-blur-sm">
                    <div className="text-xs text-zinc-500 uppercase">Passed (Clean)</div>
                    <div className="text-2xl font-bold text-emerald-400 mt-1">{qualitySummary.pass_count}</div>
                  </div>
                  <div className="bg-zinc-900/60 p-4 rounded-xl border border-zinc-800 backdrop-blur-sm">
                    <div className="text-xs text-zinc-500 uppercase">Failed</div>
                    <div className="text-2xl font-bold text-red-400 mt-1">{qualitySummary.fail_count}</div>
                  </div>
                </div>
              )}

              {/* Quality Reports List */}
              <div className="space-y-4">
                {qualityReports.map((q) => (
                  <div key={q.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                      <div className="flex items-center gap-3">
                        {getGateBadge(q.quality_gate)}
                        <span className="text-xs font-bold text-white">Score: {q.overall_score} / 100</span>
                      </div>
                      <span className="text-[11px] text-zinc-500">{new Date(q.created_at).toLocaleString()}</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800">
                        <div className="text-xs font-semibold text-indigo-300 mb-1">Ruff Static Linter Findings</div>
                        <div className="text-[11px] font-mono text-zinc-400 max-h-32 overflow-y-auto">
                          {JSON.stringify(q.lint_findings, null, 2)}
                        </div>
                      </div>

                      <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800">
                        <div className="text-xs font-semibold text-amber-300 mb-1">Bandit Security Scan Findings</div>
                        <div className="text-[11px] font-mono text-zinc-400 max-h-32 overflow-y-auto">
                          {JSON.stringify(q.security_findings, null, 2)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}
