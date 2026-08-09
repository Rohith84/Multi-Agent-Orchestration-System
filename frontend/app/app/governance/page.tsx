/**
 * Security & Enterprise Governance Studio Page.
 *
 * Features:
 * - Multi-Tenant Organization & Team Management
 * - Role-Based Access Control (RBAC) Permissions Table
 * - API Key Manager & Usage Quota Tracker
 * - Security Audit Explorer (DLP Secret Masking & Prompt Injection Defense Logs)
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ShieldCheck,
  Key,
  Users,
  Building2,
  Lock,
  Plus,
  CheckCircle2,
  ShieldAlert,
  Loader2,
  RefreshCw,
  Eye,
  Copy,
  Check,
  Terminal,
  Activity,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchUsers,
  fetchOrganizations,
  fetchTeams,
  fetchRoles,
  fetchAPIKeys,
  createAPIKey,
  fetchAuditLogs,
  type User,
  type Organization,
  type Team,
  type Role,
  type APIKey,
  type AuditLog,
} from "@/services/tenant-service";

type GovernanceTab = "rbac" | "apikeys" | "audit" | "org";

export default function GovernancePage() {
  const [activeTab, setActiveTab] = useState<GovernanceTab>("rbac");
  const [users, setUsers] = useState<User[]>([]);
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  // New API Key Modal State
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyQuota, setNewKeyQuota] = useState(100000);
  const [createdSecretKey, setCreatedSecretKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [userList, orgList, teamList, roleList, keyList, logList] = await Promise.all([
        fetchUsers(),
        fetchOrganizations(),
        fetchTeams(),
        fetchRoles(),
        fetchAPIKeys(),
        fetchAuditLogs(),
      ]);
      setUsers(userList);
      setOrgs(orgList);
      setTeams(teamList);
      setRoles(roleList);
      setApiKeys(keyList);
      setAuditLogs(logList);
    } catch (err) {
      console.error("Failed to load governance data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName) return;
    setActionLoading(true);
    try {
      const res = await createAPIKey(newKeyName, newKeyQuota);
      setCreatedSecretKey(res.api_key);
      setNewKeyName("");
      await loadData();
    } catch (err) {
      console.error("Failed to create API key:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const copySecretToClipboard = () => {
    if (!createdSecretKey) return;
    navigator.clipboard.writeText(createdSecretKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <ShieldCheck className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Security & Governance Studio</h1>
              <p className="text-sm text-zinc-400">
                Multi-Tenant Isolation • RBAC • API Key Management • DLP & Audit Logs
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
            <RefreshCw className="h-4 w-4 mr-2" /> Refresh Audit Logs
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-zinc-800 pb-3">
        {[{ id: "rbac", label: "RBAC Roles & Permissions", icon: Lock },
          { id: "apikeys", label: "API Key Manager", icon: Key },
          { id: "audit", label: "Security Audit Explorer", icon: ShieldAlert },
          { id: "org", label: "Organization & Users", icon: Building2 },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as GovernanceTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
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
          <Loader2 className="h-8 w-8 text-emerald-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* TAB 1: RBAC ROLES & Permissions */}
          {activeTab === "rbac" && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                Role-Based Access Control (RBAC) Matrix ({roles.length} Roles)
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {roles.map((role) => (
                  <div key={role.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                      <span className="text-sm font-bold text-white">{role.name}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        Active
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[11px] font-semibold text-zinc-400">Assigned Permissions:</div>
                      <div className="flex flex-wrap gap-1">
                        {role.permissions.map((perm, idx) => (
                          <span key={idx} className="text-[10px] font-mono bg-zinc-950 px-2 py-1 rounded border border-zinc-800 text-zinc-300">
                            {perm}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: API KEY MANAGER */}
          {activeTab === "apikeys" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Key List */}
              <div className="lg:col-span-2 space-y-4">
                <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                  Active API Keys ({apiKeys.length})
                </h2>

                {apiKeys.length === 0 ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-8 text-center backdrop-blur-sm">
                    <Key className="h-10 w-10 text-zinc-700 mx-auto mb-3" />
                    <p className="text-sm text-zinc-500">No API keys generated yet.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {apiKeys.map((key) => (
                      <div key={key.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 backdrop-blur-sm flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Key className="h-5 w-5 text-emerald-400" />
                          <div>
                            <div className="text-xs font-bold text-white">{key.name}</div>
                            <div className="text-[10px] font-mono text-zinc-500">Prefix: {key.prefix}...</div>
                          </div>
                        </div>

                        <div className="text-right">
                          <div className="text-xs font-bold text-emerald-400 font-mono">
                            {key.usage_count} / {key.monthly_quota} requests
                          </div>
                          <div className="text-[10px] text-zinc-500">Created: {new Date(key.created_at).toLocaleDateString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Create Key Form & Secret Reveal */}
                <div className="space-y-4">
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-4">
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <Plus className="h-4 w-4 text-emerald-400" /> Generate New API Key
                    </h3>

                    <form onSubmit={handleCreateKey} className="space-y-3">
                      <div>
                        <label className="text-[11px] font-semibold text-zinc-300 block mb-1">Key Name</label>
                        <input
                          type="text"
                          placeholder="e.g. Production Microservice"
                          value={newKeyName}
                          onChange={(e) => setNewKeyName(e.target.value)}
                          className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white placeholder-zinc-600 focus:outline-none focus:border-emerald-500"
                        />
                      </div>

                      <div>
                        <label className="text-[11px] font-semibold text-zinc-300 block mb-1">Monthly Request Quota</label>
                        <input
                          type="number"
                          value={newKeyQuota}
                          onChange={(e) => setNewKeyQuota(Number(e.target.value))}
                          className="w-full text-xs bg-zinc-950 border border-zinc-800 rounded p-2 text-white focus:outline-none focus:border-emerald-500"
                        />
                      </div>

                      <Button
                        type="submit"
                        disabled={actionLoading || !newKeyName}
                        size="sm"
                        className="w-full bg-emerald-500 hover:bg-emerald-600 text-zinc-950 font-bold text-xs"
                      >
                        Generate API Key
                      </Button>
                    </form>
                  </div>

                  {/* Secret Key Modal Result */}
                  {createdSecretKey && (
                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-2 backdrop-blur-sm">
                      <div className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                        <CheckCircle2 className="h-4 w-4" /> API Key Created! Copy secret key:
                      </div>
                      <div className="flex items-center gap-2 bg-zinc-950 p-2 rounded border border-zinc-800 font-mono text-[11px] text-white">
                        <span className="truncate flex-1">{createdSecretKey}</span>
                        <button onClick={copySecretToClipboard} className="text-emerald-400 hover:text-emerald-300">
                          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        </button>
                      </div>
                      <p className="text-[10px] text-zinc-400">Save this secret key. It will not be shown again.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SECURITY AUDIT EXPLORER */}
          {activeTab === "audit" && (
            <div className="space-y-6">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                Security & Governance Audit Log History ({auditLogs.length} Events)
              </h2>

              <div className="space-y-3">
                {auditLogs.map((log) => (
                  <div key={log.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 backdrop-blur-sm space-y-2">
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                      <div className="flex items-center gap-3">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-mono font-bold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          {log.action}
                        </span>
                        <span className="text-xs font-mono text-zinc-400">IP: {log.ip_address}</span>
                      </div>
                      <span className="text-[11px] text-zinc-500">{new Date(log.created_at).toLocaleString()}</span>
                    </div>

                    <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 font-mono text-[11px] text-zinc-300 whitespace-pre-wrap">
                      {JSON.stringify(log.details, null, 2)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: ORGANIZATION & USERS */}
          {activeTab === "org" && (
            <div className="space-y-6">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-sm space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-emerald-400" /> Organization Membership ({users.length} Users)
                </h3>

                <div className="space-y-2">
                  {users.map((u) => (
                    <div key={u.id} className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                      <div>
                        <div className="text-xs font-bold text-white">{u.full_name || u.email}</div>
                        <div className="text-[10px] text-zinc-500">{u.email}</div>
                      </div>
                      <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
                        {u.role}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}

