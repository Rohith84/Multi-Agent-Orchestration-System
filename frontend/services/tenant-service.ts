/**
 * Security & Governance Service — API client for Auth, Organizations, Teams, RBAC Roles, API Keys, and Audit Logs.
 */

import api from "@/lib/api";

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface Team {
  id: string;
  org_id: string;
  name: string;
  created_at: string;
}

export interface Role {
  id: string;
  name: string;
  permissions: string[];
}

export interface APIKey {
  id: string;
  org_id: string;
  user_id: string;
  prefix: string;
  name: string;
  is_active: boolean;
  usage_count: number;
  monthly_quota: number;
  created_at: string;
}

export interface APIKeyCreatedResponse {
  api_key: string;
  key_info: APIKey;
}

export interface AuditLog {
  id: string;
  org_id: string;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
  details: Record<string, unknown>;
  created_at: string;
}

/**
 * List organization users.
 * GET /api/users
 */
export async function fetchUsers(): Promise<User[]> {
  const { data } = await api.get<User[]>("/api/users");
  return data;
}

/**
 * List organizations.
 * GET /api/organizations
 */
export async function fetchOrganizations(): Promise<Organization[]> {
  const { data } = await api.get<Organization[]>("/api/organizations");
  return data;
}

/**
 * List sub-teams.
 * GET /api/teams
 */
export async function fetchTeams(): Promise<Team[]> {
  const { data } = await api.get<Team[]>("/api/teams");
  return data;
}

/**
 * List RBAC roles.
 * GET /api/roles
 */
export async function fetchRoles(): Promise<Role[]> {
  const { data } = await api.get<Role[]>("/api/roles");
  return data;
}

/**
 * List active API Keys.
 * GET /api/api-keys
 */
export async function fetchAPIKeys(): Promise<APIKey[]> {
  const { data } = await api.get<APIKey[]>("/api/api-keys");
  return data;
}

/**
 * Create new API Key.
 * POST /api/api-keys
 */
export async function createAPIKey(name: string, monthlyQuota: number = 100000): Promise<APIKeyCreatedResponse> {
  const { data } = await api.post<APIKeyCreatedResponse>("/api/api-keys", {
    name,
    monthly_quota: monthlyQuota,
  });
  return data;
}

/**
 * Fetch security audit logs.
 * GET /api/audit
 */
export async function fetchAuditLogs(): Promise<AuditLog[]> {
  const { data } = await api.get<AuditLog[]>("/api/audit");
  return data;
}
