/**
 * Knowledge Base page — document management and semantic indexing control.
 * Features:
 * - Drag-and-drop or select files to upload (PDF, TXT, MD, DOCX, Code)
 * - Detailed table listing all uploaded documents
 * - Single-click document deletion
 * - Re-index database embeddings trigger with a real-time progress bar
 */

"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  FileText,
  Upload,
  Trash2,
  RefreshCw,
  ArrowLeft,
  MessageSquare,
  AlertCircle,
  CheckCircle,
  Clock,
  Sparkles,
  Search,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  uploaded_at: string;
}

interface ReindexStatus {
  status: "idle" | "running" | "completed" | "failed";
  processed: number;
  total: number;
  error: string | null;
}

export default function KnowledgePage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Reindexing state
  const [reindexStatus, setReindexStatus] = useState<ReindexStatus>({
    status: "idle",
    processed: 0,
    total: 0,
    error: null,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch all documents
  const fetchDocs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/knowledge`);
      if (!res.ok) throw new Error("Failed to fetch documents");
      const data = await res.json();
      setDocuments(data);
    } catch (err: any) {
      console.error(err);
      showMsg("error", "Failed to load documents list from backend.");
    } finally {
      setLoadingDocs(false);
    }
  };

  // Poll reindexing progress
  const pollReindexProgress = async () => {
    try {
      const res = await fetch(`${API_URL}/api/knowledge/reindex/progress`);
      if (!res.ok) throw new Error("Failed to check reindexing status");
      const data = await res.json();
      setReindexStatus(data);

      // Stop polling if completed or failed
      if (data.status === "completed" || data.status === "failed") {
        if (data.status === "completed") {
          showMsg("success", `Reindexing completed! Generated vectors for ${data.total} chunks.`);
        } else {
          showMsg("error", `Reindexing failed: ${data.error}`);
        }
        return false;
      }
      return true;
    } catch (err) {
      console.error(err);
      return false;
    }
  };

  useEffect(() => {
    fetchDocs();
    
    // Check initial reindexing status
    pollReindexProgress();
  }, []);

  // Set up polling interval when reindexing is running
  useEffect(() => {
    let intervalId: any = null;

    if (reindexStatus.status === "running") {
      intervalId = setInterval(async () => {
        const keepPolling = await pollReindexProgress();
        if (!keepPolling) {
          clearInterval(intervalId);
        }
      }, 1500);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [reindexStatus.status]);

  const showMsg = (type: "success" | "error", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  // Handle Drag & Drop
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  // Upload file
  const uploadFile = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/api/knowledge/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      showMsg("success", `File "${file.name}" uploaded and chunk-indexed successfully.`);
      fetchDocs();
    } catch (err: any) {
      console.error(err);
      showMsg("error", err.message || "Failed to upload document.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Delete document
  const deleteDoc = async (id: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? This removes database chunks and ChromaDB embeddings.`)) {
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/knowledge/${id}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Delete failed");
      }

      showMsg("success", `Document "${filename}" was deleted successfully.`);
      fetchDocs();
    } catch (err: any) {
      console.error(err);
      showMsg("error", err.message || "Failed to delete document.");
    }
  };

  // Trigger Reindexing
  const triggerReindex = async () => {
    try {
      const res = await fetch(`${API_URL}/api/knowledge/reindex`, {
        method: "POST",
      });

      if (!res.ok) throw new Error("Failed to start reindexing");

      setReindexStatus((prev) => ({
        ...prev,
        status: "running",
        processed: 0,
        total: 0,
      }));
      showMsg("success", "Reindexing started in the background.");
    } catch (err: any) {
      console.error(err);
      showMsg("error", err.message || "Failed to trigger reindexing.");
    }
  };

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Formatting utils
  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  };

  // Progress percentage calculation
  const progressPercent = reindexStatus.total > 0
    ? Math.round((reindexStatus.processed / reindexStatus.total) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col font-sans">
      {/* Navigation Header */}
      <header className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/40 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/">
            <div className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors cursor-pointer">
              <ArrowLeft className="h-4 w-4" />
            </div>
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-violet-400" />
              Knowledge Base
            </h1>
            <p className="text-xs text-zinc-500 mt-0.5">
              Upload documents to embed &amp; query semantic knowledge
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/chat">
            <Button size="sm" className="bg-violet-600 hover:bg-violet-700 text-white font-medium shadow-lg shadow-violet-500/20">
              <MessageSquare className="h-4 w-4 mr-1.5" />
              Chat Assistant
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto w-full grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Left Column: Upload & Actions */}
        <div className="space-y-6">
          {/* Notifications banner */}
          {message && (
            <div
              className={`p-4 rounded-xl border flex items-start gap-3 animate-in fade-in slide-in-from-top-2 duration-300 ${
                message.type === "success"
                  ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                  : "bg-red-500/10 border-red-500/20 text-red-400"
              }`}
            >
              {message.type === "success" ? (
                <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              )}
              <div className="text-xs font-medium leading-relaxed">
                {message.text}
              </div>
            </div>
          )}

          {/* Upload Card */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/20 backdrop-blur-sm p-6 space-y-4">
            <h2 className="text-sm font-semibold text-white">Upload Documents</h2>
            <p className="text-xs text-zinc-500">
              Support PDF, TXT, Markdown, DOCX, and raw Source Code files.
            </p>
            
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all duration-300 ${
                dragActive
                  ? "border-violet-500 bg-violet-500/5"
                  : "border-zinc-800 hover:border-zinc-700 bg-zinc-950/20 hover:bg-zinc-950/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileChange}
                accept=".pdf,.docx,.txt,.md,.markdown,.py,.js,.ts,.tsx,.html,.css,.json,.go,.rs,.sh"
              />
              <div className={`p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 transition-transform ${uploading ? "animate-bounce" : ""}`}>
                <Upload className="h-5 w-5" />
              </div>
              <div className="text-center">
                <p className="text-xs font-medium text-zinc-300">
                  {uploading ? "Indexing file..." : "Drag & drop or click to upload"}
                </p>
                <p className="text-[10px] text-zinc-500 mt-1">
                  Maximum size: 20MB
                </p>
              </div>
            </div>
          </div>

          {/* Indexing status & Re-index trigger */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/20 backdrop-blur-sm p-6 space-y-4">
            <h2 className="text-sm font-semibold text-white">Index Operations</h2>
            <p className="text-xs text-zinc-500">
              Re-embed and sync Postgres chunks with ChromaDB. Run this after vector store resets.
            </p>

            {reindexStatus.status === "running" ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-violet-400 flex items-center gap-1.5">
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Reindexing vectors...
                  </span>
                  <span className="text-zinc-400 font-mono">
                    {reindexStatus.processed} / {reindexStatus.total} ({progressPercent}%)
                  </span>
                </div>
                <div className="w-full bg-zinc-950 rounded-full h-2 overflow-hidden border border-zinc-800">
                  <div
                    className="bg-gradient-to-r from-violet-600 to-blue-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            ) : (
              <Button
                onClick={triggerReindex}
                variant="outline"
                className="w-full border-zinc-800 bg-zinc-950 hover:bg-zinc-900 text-zinc-300 hover:text-white cursor-pointer"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Re-index Knowledge Base
              </Button>
            )}
            
            {reindexStatus.status !== "idle" && reindexStatus.status !== "running" && (
              <div className="flex items-center gap-2 text-[10px] text-zinc-500">
                <Clock className="h-3 w-3" />
                <span>Last action: {reindexStatus.status}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Files List Table */}
        <div className="md:col-span-2 space-y-6">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/20 backdrop-blur-sm p-6 flex flex-col h-[520px] overflow-hidden">
            {/* Table Header Controls */}
            <div className="flex items-center justify-between gap-4 mb-6">
              <h2 className="text-sm font-semibold text-white">
                Indexed Documents ({documents.length})
              </h2>
              
              <div className="relative max-w-xs w-full">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Search file name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-zinc-800 bg-zinc-950/50 text-zinc-300 placeholder-zinc-500 focus:outline-none focus:border-zinc-700 transition-colors"
                />
              </div>
            </div>

            {/* Scrollable table container */}
            <div className="flex-1 overflow-y-auto border border-zinc-800/80 rounded-xl bg-zinc-950/20">
              {loadingDocs ? (
                <div className="h-full flex items-center justify-center flex-col gap-2 text-zinc-500">
                  <RefreshCw className="h-5 w-5 animate-spin text-violet-400" />
                  <span className="text-xs">Loading files...</span>
                </div>
              ) : filteredDocs.length === 0 ? (
                <div className="h-full flex items-center justify-center flex-col gap-2 text-zinc-600">
                  <FileText className="h-10 w-10 text-zinc-850" />
                  <span className="text-xs font-medium">No documents found</span>
                  <span className="text-[10px] text-zinc-600 mt-0.5">Upload document above to begin indexing.</span>
                </div>
              ) : (
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-400 font-semibold bg-zinc-900/20">
                      <th className="p-4">Name</th>
                      <th className="p-4">Type</th>
                      <th className="p-4">Indexed At</th>
                      <th className="p-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDocs.map((doc) => (
                      <tr
                        key={doc.id}
                        className="border-b border-zinc-800/60 hover:bg-zinc-800/20 transition-colors text-zinc-300"
                      >
                        <td className="p-4 font-medium max-w-xs truncate" title={doc.filename}>
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-blue-400 shrink-0" />
                            <span className="truncate">{doc.filename}</span>
                          </div>
                        </td>
                        <td className="p-4">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-400 font-semibold">
                            {doc.file_type}
                          </span>
                        </td>
                        <td className="p-4 text-zinc-500 font-mono">
                          {formatTime(doc.uploaded_at)}
                        </td>
                        <td className="p-4 text-right">
                          <Button
                            onClick={() => deleteDoc(doc.id, doc.filename)}
                            variant="ghost"
                            size="sm"
                            className="text-zinc-500 hover:text-red-400 hover:bg-red-500/10 p-2 h-auto cursor-pointer"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
