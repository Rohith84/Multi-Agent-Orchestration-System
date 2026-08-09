/**
 * /app/knowledge — Canonical Knowledge Base route inside the /app/* application shell.
 *
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
    pollReindexProgress();
  }, []);

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

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  };

  const progressPercent = reindexStatus.total > 0
    ? Math.round((reindexStatus.processed / reindexStatus.total) * 100)
    : 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header Card */}
      <div className="p-6 brutalist-card flex flex-col sm:flex-row sm:items-center justify-between gap-4" style={{ background: "var(--bg-surface)" }}>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5 text-[var(--accent-secondary)]" />
            <h1 className="text-h1 font-black tracking-tight uppercase" style={{ color: "var(--fg-primary)" }}>
              Knowledge Base
            </h1>
          </div>
          <p className="text-body-sm text-[var(--fg-secondary)]">
            Upload &amp; manage document embeddings for multi-agent RAG vector retrieval
          </p>
        </div>

        <Link href="/app/chat">
          <Button size="sm" className="brutalist-btn brutalist-btn-primary text-xs">
            <MessageSquare className="w-4 h-4 mr-1.5" />
            Chat Assistant →
          </Button>
        </Link>
      </div>

      {/* Main Container Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Left Column: Upload & Reindexing Controls */}
        <div className="space-y-6">
          {/* Notifications banner */}
          {message && (
            <div
              className={`p-4 border-2 flex items-start gap-3 ${
                message.type === "success"
                  ? "bg-emerald-500/10 border-emerald-500 text-emerald-400"
                  : "bg-red-500/10 border-red-500 text-red-400"
              }`}
            >
              {message.type === "success" ? (
                <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              )}
              <div className="text-xs font-bold leading-relaxed">
                {message.text}
              </div>
            </div>
          )}

          {/* Upload Card */}
          <div className="p-5 brutalist-card space-y-4" style={{ background: "var(--bg-surface)" }}>
            <h3 className="text-xs font-black uppercase text-[var(--fg-primary)] border-b-2 border-[var(--border-primary)] pb-2 flex items-center gap-2">
              <Upload className="h-4 w-4 text-[var(--accent-primary)]" />
              Upload Document
            </h3>

            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`p-6 border-2 border-dashed rounded-lg text-center cursor-pointer transition-all ${
                dragActive
                  ? "border-[var(--accent-primary)] bg-[var(--bg-secondary)]"
                  : "border-[var(--border-secondary)] hover:border-[var(--border-primary)]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileChange}
                accept=".pdf,.txt,.md,.docx,.py,.js,.ts,.json"
              />

              <Upload className="h-8 w-8 mx-auto text-[var(--fg-tertiary)] mb-2" />
              <p className="text-xs font-bold text-[var(--fg-primary)] uppercase">
                {uploading ? "Uploading & Indexing..." : "Click or drag file to upload"}
              </p>
              <p className="text-[10px] text-[var(--fg-tertiary)] mt-1">
                Supports PDF, TXT, MD, DOCX, Code files
              </p>
            </div>
          </div>

          {/* Reindexing Status Card */}
          <div className="p-5 brutalist-card space-y-4" style={{ background: "var(--bg-surface)" }}>
            <div className="flex items-center justify-between border-b-2 border-[var(--border-primary)] pb-2">
              <h3 className="text-xs font-black uppercase text-[var(--fg-primary)] flex items-center gap-2">
                <RefreshCw className={`h-4 w-4 text-[var(--accent-secondary)] ${reindexStatus.status === "running" ? "animate-spin" : ""}`} />
                RAG Vector Index
              </h3>

              <button
                onClick={triggerReindex}
                disabled={reindexStatus.status === "running"}
                className="brutalist-btn brutalist-btn-secondary text-[10px] py-1 px-2"
              >
                Re-Index All
              </button>
            </div>

            {reindexStatus.status === "running" ? (
              <div className="space-y-2">
                <div className="flex justify-between text-caption text-[var(--fg-secondary)]">
                  <span>Reindexing vectors...</span>
                  <span>{progressPercent}%</span>
                </div>
                <div className="w-full h-2 bg-[var(--bg-primary)] border border-[var(--border-secondary)] overflow-hidden">
                  <div className="h-full bg-[var(--accent-primary)] transition-all duration-300" style={{ width: `${progressPercent}%` }} />
                </div>
                <p className="text-[10px] text-[var(--fg-tertiary)] text-right">
                  {reindexStatus.processed} / {reindexStatus.total} chunks
                </p>
              </div>
            ) : (
              <p className="text-caption text-[var(--fg-tertiary)]">
                Status: <span className="font-bold uppercase text-[var(--fg-primary)]">{reindexStatus.status}</span>. Click re-index to refresh ChromaDB vector embeddings.
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Uploaded Documents Table */}
        <div className="md:col-span-2 p-5 brutalist-card space-y-4" style={{ background: "var(--bg-surface)" }}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b-2 border-[var(--border-primary)] pb-3">
            <h3 className="text-xs font-black uppercase text-[var(--fg-primary)] flex items-center gap-2">
              <FileText className="h-4 w-4 text-[var(--accent-success)]" />
              Indexed Documents ({filteredDocs.length})
            </h3>

            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--fg-tertiary)]" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 border-2 border-[var(--border-secondary)] bg-[var(--bg-primary)] text-xs font-bold text-[var(--fg-primary)] focus:outline-none"
              />
            </div>
          </div>

          {loadingDocs ? (
            <div className="text-caption text-[var(--fg-tertiary)] py-12 text-center">
              Loading documents from knowledge base...
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="p-8 border-2 border-dashed border-[var(--border-secondary)] text-center text-caption text-[var(--fg-tertiary)]">
              No documents found in knowledge index. Upload a file to get started.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b-2 border-[var(--border-primary)] text-[10px] font-black uppercase text-[var(--fg-tertiary)]">
                    <th className="p-2">Filename</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Uploaded</th>
                    <th className="p-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-secondary)]">
                  {filteredDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-[var(--bg-secondary)] text-xs font-mono">
                      <td className="p-2 font-bold text-[var(--fg-primary)] max-w-xs truncate">
                        {doc.filename}
                      </td>
                      <td className="p-2 uppercase text-[10px] font-bold text-[var(--accent-secondary)]">
                        {doc.file_type}
                      </td>
                      <td className="p-2 text-[10px] text-[var(--fg-tertiary)]">
                        {formatTime(doc.uploaded_at)}
                      </td>
                      <td className="p-2 text-right">
                        <button
                          onClick={() => deleteDoc(doc.id, doc.filename)}
                          className="p-1 text-[var(--fg-tertiary)] hover:text-[var(--accent-error)] transition-colors"
                          title="Delete Document"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
