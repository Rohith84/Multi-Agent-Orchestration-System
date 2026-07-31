/**
 * Artifact Studio Service — API client for interactive artifacts, version control, side-by-side diffs, and vision analysis.
 */

import api from "@/lib/api";

export interface ArtifactVersion {
  id: string;
  artifact_id: string;
  version: number;
  parent_version?: number;
  content: string;
  creator_agent: string;
  change_summary: string;
  created_at: string;
}

export interface Artifact {
  id: string;
  session_id: string;
  title: string;
  artifact_type: string;
  creator_agent: string;
  current_version: number;
  preview_type: string;
  created_at: string;
  updated_at: string;
  versions: ArtifactVersion[];
}

export interface ArtifactDiff {
  artifact_id: string;
  version_a: number;
  version_b: number;
  content_a: string;
  content_b: string;
  diff_lines: string[];
}

export interface VisionAnalysisResult {
  status: string;
  file_type: string;
  analysis: string;
  prompt_used: string;
}

/**
 * List session artifacts.
 * GET /api/artifacts
 */
export async function fetchArtifacts(): Promise<Artifact[]> {
  const { data } = await api.get<Artifact[]>("/api/artifacts");
  return data;
}

/**
 * Fetch artifact details.
 * GET /api/artifacts/{id}
 */
export async function fetchArtifactDetails(artifactId: string): Promise<Artifact> {
  const { data } = await api.get<Artifact>(`/api/artifacts/${artifactId}`);
  return data;
}

/**
 * Create a new artifact.
 * POST /api/artifacts
 */
export async function createArtifact(payload: {
  title: string;
  artifact_type: string;
  preview_type: string;
  content: string;
}): Promise<Artifact> {
  const { data } = await api.post<Artifact>("/api/artifacts", payload);
  return data;
}

/**
 * Restore artifact version.
 * POST /api/artifacts/{id}/restore
 */
export async function restoreArtifactVersion(artifactId: string, version: number): Promise<Artifact> {
  const { data } = await api.post<Artifact>(`/api/artifacts/${artifactId}/restore`, { version });
  return data;
}

/**
 * Fetch side-by-side diff.
 * GET /api/artifacts/{id}/diff
 */
export async function fetchArtifactDiff(artifactId: string, versionA: number, versionB: number): Promise<ArtifactDiff> {
  const { data } = await api.get<ArtifactDiff>(`/api/artifacts/${artifactId}/diff`, {
    params: { version_a: versionA, version_b: versionB },
  });
  return data;
}

/**
 * Analyze vision base64 image/diagram.
 * POST /api/artifacts/vision/analyze
 */
export async function analyzeVisionImage(payload: {
  image_base64: string;
  file_type: string;
  prompt?: string;
}): Promise<VisionAnalysisResult> {
  const { data } = await api.post<VisionAnalysisResult>("/api/artifacts/vision/analyze", payload);
  return data;
}
