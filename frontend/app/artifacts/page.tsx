/**
 * Multi-Modal AI Development Studio & Artifact Workspace Page.
 *
 * Features:
 * - Live Component Preview Sandbox (Desktop / Tablet / Mobile viewports)
 * - Multi-Modal Vision Image / Wireframe Analyzer
 * - Side-by-Side Version Diff Inspector
 * - Interactive Mermaid Diagram Viewer
 * - Multi-format Export Controls (ZIP, Markdown, JSON)
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Sparkles,
  Eye,
  Code2,
  GitCompare,
  Upload,
  Download,
  Smartphone,
  Tablet,
  Monitor,
  RotateCcw,
  CheckCircle2,
  Loader2,
  Layers,
  FileText,
  Image as ImageIcon,
  ChevronRight,
  RefreshCw,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchArtifacts,
  fetchArtifactDetails,
  restoreArtifactVersion,
  fetchArtifactDiff,
  analyzeVisionImage,
  type Artifact,
  type ArtifactDiff,
  type VisionAnalysisResult,
} from "@/services/artifact-service";

type StudioTab = "preview" | "code" | "diff" | "vision";
type ViewportMode = "desktop" | "tablet" | "mobile";

export default function ArtifactsPage() {
  const [activeTab, setActiveTab] = useState<StudioTab>("preview");
  const [viewport, setViewport] = useState<ViewportMode>("desktop");
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [selectedVersionNum, setSelectedVersionNum] = useState<number>(1);
  const [diffData, setDiffData] = useState<ArtifactDiff | null>(null);
  const [visionResult, setVisionResult] = useState<VisionAnalysisResult | null>(null);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [visionImageBase64, setVisionImageBase64] = useState<string>("");

  const loadData = useCallback(async () => {
    try {
      const list = await fetchArtifacts();
      setArtifacts(list);
      if (list.length > 0 && !selectedArtifact) {
        setSelectedArtifact(list[0]);
        setSelectedVersionNum(list[0].current_version);
      }
    } catch (err) {
      console.error("Failed to load artifacts:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedArtifact]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelectArtifact = async (art: Artifact) => {
    setSelectedArtifact(art);
    setSelectedVersionNum(art.current_version);
    setDiffData(null);
  };

  const handleFetchDiff = async () => {
    if (!selectedArtifact || selectedArtifact.versions.length < 2) return;
    setActionLoading(true);
    try {
      const vA = selectedArtifact.current_version - 1;
      const vB = selectedArtifact.current_version;
      const diff = await fetchArtifactDiff(selectedArtifact.id, vA, vB);
      setDiffData(diff);
      setActiveTab("diff");
    } catch (err) {
      console.error("Failed to fetch diff:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRestoreVersion = async (vNum: number) => {
    if (!selectedArtifact) return;
    setActionLoading(true);
    try {
      const updated = await restoreArtifactVersion(selectedArtifact.id, vNum);
      setSelectedArtifact(updated);
      setSelectedVersionNum(updated.current_version);
      await loadData();
    } catch (err) {
      console.error("Failed to restore version:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (evt) => {
      const base64 = evt.target?.result as string;
      setVisionImageBase64(base64);
      setActionLoading(true);
      try {
        const rawBase64 = base64.split(",")[1] || base64;
        const res = await analyzeVisionImage({
          image_base64: rawBase64,
          file_type: file.type.split("/")[1] || "png",
        });
        setVisionResult(res);
        setActiveTab("vision");
      } catch (err) {
        console.error("Failed to analyze vision image:", err);
      } finally {
        setActionLoading(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const getCurrentContent = () => {
    if (!selectedArtifact) return "";
    const vObj = selectedArtifact.versions.find((v) => v.version === selectedVersionNum);
    return vObj ? vObj.content : selectedArtifact.versions[0]?.content || "";
  };

  const getViewportWidthClass = () => {
    switch (viewport) {
      case "tablet":
        return "max-w-[768px]";
      case "mobile":
        return "max-w-[375px]";
      default:
        return "w-full";
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
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Multi-Modal AI Development Studio</h1>
              <p className="text-sm text-zinc-400">
                Live UI Sandbox • Vision Diagram Analysis • Side-by-Side Diff • Artifact Versioning
              </p>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <label className="cursor-pointer">
            <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
            <div className="inline-flex items-center justify-center rounded-md text-xs font-medium transition-colors border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10 h-9 px-3 py-2 cursor-pointer">
              <Upload className="h-4 w-4 mr-2" /> Upload Sketch / Diagram
            </div>
          </label>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-24">
          <Loader2 className="h-8 w-8 text-violet-400 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Artifact Explorer Sidebar */}
          <div className="space-y-4">
            <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              Artifact Library ({artifacts.length})
            </h2>

            {artifacts.length === 0 ? (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 text-center backdrop-blur-sm">
                <Layers className="h-8 w-8 text-zinc-700 mx-auto mb-2" />
                <p className="text-xs text-zinc-500">No artifacts generated yet.</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                {artifacts.map((art) => {
                  const isSelected = selectedArtifact?.id === art.id;
                  return (
                    <div
                      key={art.id}
                      onClick={() => handleSelectArtifact(art)}
                      className={`p-3 rounded-lg border backdrop-blur-sm cursor-pointer transition-all ${
                        isSelected
                          ? "bg-zinc-800/80 border-violet-500/40 ring-1 ring-violet-500/30"
                          : "bg-zinc-900/40 border-zinc-800 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white truncate max-w-[160px]">{art.title}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-violet-500/20 text-violet-300">
                          v{art.current_version}
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-500 mt-1 capitalize">
                        Type: {art.artifact_type} • Agent: {art.creator_agent}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Version History Selector */}
            {selectedArtifact && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-2 backdrop-blur-sm">
                <h3 className="text-xs font-semibold text-zinc-300">Version History</h3>
                <div className="space-y-1">
                  {selectedArtifact.versions.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => setSelectedVersionNum(v.version)}
                      className={`w-full text-left px-2.5 py-1.5 rounded text-xs flex items-center justify-between ${
                        selectedVersionNum === v.version
                          ? "bg-violet-600 text-white font-bold"
                          : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
                      }`}
                    >
                      <span>v{v.version} — {v.change_summary}</span>
                      {selectedVersionNum !== v.version && (
                        <RotateCcw
                          className="h-3 w-3 text-zinc-500 hover:text-white shrink-0"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRestoreVersion(v.version);
                          }}
                        />
                      )}
                    </button>
                  ))}
                </div>
                {selectedArtifact.versions.length >= 2 && (
                  <Button
                    onClick={handleFetchDiff}
                    disabled={actionLoading}
                    variant="outline"
                    size="sm"
                    className="w-full mt-2 border-zinc-700 text-zinc-300 text-xs"
                  >
                    <GitCompare className="h-3.5 w-3.5 mr-1.5" /> Compare Versions
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* Studio Workspace Canvas */}
          <div className="lg:col-span-3 space-y-4">
            {/* Top Workspace Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 pb-3">
              <div className="flex gap-2">
                {[
                  { id: "preview", label: "Live Sandbox Preview", icon: Eye },
                  { id: "code", label: "Source Code", icon: Code2 },
                  { id: "diff", label: "Side-by-Side Diff", icon: GitCompare },
                  { id: "vision", label: "Vision Analysis", icon: ImageIcon },
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as StudioTab)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        isActive
                          ? "bg-violet-500/20 text-violet-300 border border-violet-500/30"
                          : "text-zinc-400 hover:text-white hover:bg-zinc-800/40"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Viewport controls for Live Sandbox */}
              {activeTab === "preview" && (
                <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 p-1 rounded-lg">
                  <button
                    onClick={() => setViewport("desktop")}
                    className={`p-1.5 rounded ${viewport === "desktop" ? "bg-zinc-800 text-white" : "text-zinc-400"}`}
                  >
                    <Monitor className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setViewport("tablet")}
                    className={`p-1.5 rounded ${viewport === "tablet" ? "bg-zinc-800 text-white" : "text-zinc-400"}`}
                  >
                    <Tablet className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setViewport("mobile")}
                    className={`p-1.5 rounded ${viewport === "mobile" ? "bg-zinc-800 text-white" : "text-zinc-400"}`}
                  >
                    <Smartphone className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>

            {/* TAB 1: LIVE SANDBOX PREVIEW */}
            {activeTab === "preview" && (
              <div className="flex flex-col items-center">
                <div className={`transition-all duration-300 border border-zinc-800 rounded-xl overflow-hidden bg-white shadow-2xl ${getViewportWidthClass()}`}>
                  <iframe
                    srcDoc={getCurrentContent() || "<h2 style='font-family:sans-serif;padding:2rem;text-align:center;'>No UI component preview available</h2>"}
                    className="w-full h-[550px] border-0"
                    title="Live Sandbox Preview"
                    sandbox="allow-scripts"
                  />
                </div>
              </div>
            )}

            {/* TAB 2: SOURCE CODE */}
            {activeTab === "code" && (
              <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 max-h-[550px] overflow-y-auto">
                <pre className="text-xs font-mono text-zinc-200 whitespace-pre-wrap leading-relaxed">
                  {getCurrentContent() || "// Select an artifact to inspect source code"}
                </pre>
              </div>
            )}

            {/* TAB 3: SIDE-BY-SIDE DIFF */}
            {activeTab === "diff" && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-3 backdrop-blur-sm">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <GitCompare className="h-4 w-4 text-violet-400" /> Side-by-Side Version Diff
                </h3>
                {diffData ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-zinc-950 p-3 rounded-lg border border-red-500/20">
                      <div className="text-xs font-semibold text-red-400 mb-1">Version {diffData.version_a}</div>
                      <pre className="text-[11px] font-mono text-zinc-400 max-h-[400px] overflow-y-auto whitespace-pre-wrap">
                        {diffData.content_a}
                      </pre>
                    </div>
                    <div className="bg-zinc-950 p-3 rounded-lg border border-emerald-500/20">
                      <div className="text-xs font-semibold text-emerald-400 mb-1">Version {diffData.version_b}</div>
                      <pre className="text-[11px] font-mono text-zinc-400 max-h-[400px] overflow-y-auto whitespace-pre-wrap">
                        {diffData.content_b}
                      </pre>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-xs text-zinc-500">
                    Click &quot;Compare Versions&quot; in the sidebar to generate a version diff.
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: VISION ANALYSIS */}
            {activeTab === "vision" && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4 backdrop-blur-sm">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <ImageIcon className="h-4 w-4 text-indigo-400" /> Multi-Modal Vision Analysis Report
                </h3>
                {visionResult ? (
                  <div className="space-y-3">
                    <div className="bg-zinc-950 p-4 rounded-lg border border-zinc-800 text-xs font-mono text-zinc-200 whitespace-pre-wrap leading-relaxed">
                      {visionResult.analysis}
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-xs text-zinc-500">
                    Upload an image or UI sketch using the button above to view vision analysis results.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
