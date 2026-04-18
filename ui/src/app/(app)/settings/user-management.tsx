"use client";

/**
 * Admin-only "Users & Activity" tab for the Settings page.
 *
 * Extracted from settings/page.tsx so it can ship as a separate async
 * chunk via next/dynamic. Non-admin visitors (the majority) never
 * download it; admins only pay for it when they click the tab.
 *
 * ~460 lines / ~10 KB gzipped of state + UI that used to live in the
 * settings-page chunk. The extraction is safe because the helpers it
 * depends on (ROLE_COLORS, ACTION_LABELS, timeAgo) are only referenced
 * inside this component.
 */

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Activity,
  Filter,
  Loader2,
  LogIn,
  RefreshCw,
  UserCheck,
  UserX,
  Users,
} from "lucide-react";
import * as api from "@/lib/api";
import { useAppStore } from "@/store";
import type { UserWithActivity, UserManagementStats, AuditLogEntry } from "@/types";

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-500/10 text-red-400 border-red-500/30",
  analyst: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  viewer: "bg-slate-500/10 text-slate-400 border-slate-500/30",
};

const ACTION_LABELS: Record<string, string> = {
  login: "Login",
  logout: "Logout",
  update_user: "User Update",
  trigger_feed: "Feed Trigger",
  trigger_all_feeds: "All Feeds",
  attack_remap: "ATT&CK Remap",
  opensearch_reindex: "Reindex",
  create: "Create",
  update: "Update",
  delete: "Delete",
};

function timeAgo(iso: string | null): string {
  if (!iso) return "Never";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60000);
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function UserManagementSettings() {
  const [users, setUsers] = useState<UserWithActivity[]>([]);
  const [stats, setStats] = useState<UserManagementStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [tab, setTab] = useState<"users" | "audit">("users");
  const [filterRole, setFilterRole] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [searchQ, setSearchQ] = useState("");

  // Audit log state
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditPages, setAuditPages] = useState(1);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditAction, setAuditAction] = useState("");
  const [auditUser, setAuditUser] = useState("");

  const currentUser = useAppStore((s) => s.user);

  const load = async () => {
    setLoading(true);
    try {
      const [u, s] = await Promise.all([api.getAdminUsers(), api.getUserManagementStats()]);
      setUsers(u);
      setStats(s);
    } catch {
      // silent
    }
    setLoading(false);
  };

  const loadAudit = async (page = 1) => {
    setAuditLoading(true);
    try {
      const res = await api.getAuditLog({
        page,
        page_size: 25,
        action: auditAction || undefined,
        user_id: auditUser || undefined,
      });
      setAuditLogs(res.logs);
      setAuditTotal(res.total);
      setAuditPage(res.page);
      setAuditPages(res.pages);
    } catch {
      // silent
    }
    setAuditLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (tab === "audit") loadAudit(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const handleRoleChange = async (userId: string, role: string) => {
    setSaving(userId);
    try {
      await api.updateAdminUser(userId, { role });
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role: role as any } : u));
    } catch {
      // silent
    }
    setSaving(null);
  };

  const handleToggleActive = async (userId: string, current: boolean) => {
    setSaving(userId + "_active");
    try {
      await api.updateAdminUser(userId, { is_active: !current });
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, is_active: !current } : u));
    } catch {
      // silent
    }
    setSaving(null);
  };

  const filtered = users.filter((u) => {
    if (filterRole !== "all" && u.role !== filterRole) return false;
    if (filterStatus === "active" && !u.is_active) return false;
    if (filterStatus === "inactive" && u.is_active) return false;
    if (searchQ && !u.email.toLowerCase().includes(searchQ.toLowerCase()) && !(u.name || "").toLowerCase().includes(searchQ.toLowerCase())) return false;
    return true;
  });

  const sortedUsers = [...filtered].sort((a, b) => {
    // Active first, then by last login desc
    if (a.is_active !== b.is_active) return a.is_active ? -1 : 1;
    const la = a.last_login ? new Date(a.last_login).getTime() : 0;
    const lb = b.last_login ? new Date(b.last_login).getTime() : 0;
    return lb - la;
  });

  return (
    <div className="space-y-4">
      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: "Total Users", value: stats.total_users, color: "text-foreground", sub: `${stats.active_users} active` },
            { label: "Active 7d", value: stats.active_7d, color: "text-emerald-400", sub: "had activity" },
            { label: "Never Logged In", value: stats.never_logged_in, color: "text-amber-400", sub: "pending users" },
            { label: "Role Split", value: `${stats.admins}A · ${stats.analysts}An · ${stats.viewers}V`, color: "text-blue-400", sub: "admin · analyst · viewer" },
          ].map((s) => (
            <div key={s.label} className="p-2.5 rounded-lg bg-muted/20 border border-border/20 text-center">
              <div className={`text-base font-bold ${s.color}`}>{s.value}</div>
              <div className="text-[9px] text-muted-foreground">{s.label}</div>
              <div className="text-[8px] text-muted-foreground/50 mt-0.5">{s.sub}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tab switch */}
      <div className="flex items-center gap-1 p-0.5 bg-muted/20 rounded-lg border border-border/20 w-fit">
        <button
          onClick={() => setTab("users")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${tab === "users" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"}`}
        >
          <Users className="h-3.5 w-3.5" /> Users
        </button>
        <button
          onClick={() => setTab("audit")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${tab === "audit" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"}`}
        >
          <Activity className="h-3.5 w-3.5" /> Audit Log
        </button>
      </div>

      {/* ── USERS TAB ── */}
      {tab === "users" && (
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Users className="h-4 w-4 text-primary" />
                User Roster
              </CardTitle>
              <div className="flex items-center gap-2 flex-wrap">
                {/* Search */}
                <input
                  type="text"
                  placeholder="Search email or name..."
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  className="h-7 px-2.5 w-40 rounded-md bg-muted/30 border border-border/40 text-[10px] focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
                {/* Role filter */}
                <select
                  value={filterRole}
                  onChange={(e) => setFilterRole(e.target.value)}
                  className="h-7 px-2 rounded-md bg-muted/30 border border-border/40 text-[10px]"
                >
                  <option value="all">All Roles</option>
                  <option value="admin">Admin</option>
                  <option value="analyst">Analyst</option>
                  <option value="viewer">Viewer</option>
                </select>
                {/* Status filter */}
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="h-7 px-2 rounded-md bg-muted/30 border border-border/40 text-[10px]"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
                <button
                  onClick={load}
                  className="h-7 w-7 flex items-center justify-center rounded-md border border-border/40 hover:bg-muted/40 transition-colors"
                  title="Refresh"
                >
                  <RefreshCw className="h-3 w-3 text-muted-foreground" />
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => <div key={i} className="h-16 rounded-lg bg-muted/20 animate-pulse" />)}
              </div>
            ) : sortedUsers.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">No users found.</p>
            ) : (
              <div className="space-y-2">
                {sortedUsers.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  const isSaving = saving === u.id;
                  const isSavingActive = saving === u.id + "_active";
                  return (
                    <div
                      key={u.id}
                      className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${u.is_active ? "bg-muted/10 border-border/20 hover:border-border/40" : "bg-muted/5 border-border/10 opacity-60"
                        }`}
                    >
                      {/* Avatar initials */}
                      <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                        <span className="text-[10px] font-bold text-primary uppercase">
                          {(u.name || u.email).slice(0, 2)}
                        </span>
                      </div>

                      {/* Identity */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-xs font-medium truncate">{u.name || u.email.split("@")[0]}</p>
                          {isSelf && (
                            <Badge variant="outline" className="text-[8px] px-1 py-0 border-primary/40 text-primary">
                              You
                            </Badge>
                          )}
                          {!u.is_active && (
                            <Badge variant="outline" className="text-[8px] px-1 py-0 border-red-500/40 text-red-400">
                              Suspended
                            </Badge>
                          )}
                        </div>
                        <p className="text-[10px] text-muted-foreground truncate">{u.email}</p>
                        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
                          <span className="flex items-center gap-0.5 text-[9px] text-muted-foreground/50">
                            <LogIn className="h-2.5 w-2.5" />
                            {timeAgo(u.last_login)} · {u.activity.login_count} logins
                          </span>
                          <span className="flex items-center gap-0.5 text-[9px] text-muted-foreground/50">
                            <Activity className="h-2.5 w-2.5" />
                            {u.activity.total_actions} actions total · {u.activity.actions_7d} this week
                          </span>
                          {u.activity.last_action_type && (
                            <span className="text-[9px] text-muted-foreground/40">
                              Last: {ACTION_LABELS[u.activity.last_action_type] || u.activity.last_action_type}
                            </span>
                          )}
                          {u.created_at && (
                            <span className="text-[9px] text-muted-foreground/40">
                              Joined {new Date(u.created_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Role change */}
                      <select
                        value={u.role}
                        disabled={isSelf || isSaving}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className={`h-7 px-2 rounded-md border text-[10px] font-medium transition-colors bg-background ${ROLE_COLORS[u.role]} disabled:opacity-50 disabled:cursor-not-allowed`}
                        title={isSelf ? "Cannot change your own role" : "Change role"}
                      >
                        <option value="admin">Admin</option>
                        <option value="analyst">Analyst</option>
                        <option value="viewer">Viewer</option>
                      </select>

                      {/* Active toggle */}
                      <button
                        disabled={isSelf || isSavingActive}
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        className={`flex items-center gap-1 h-7 px-2.5 rounded-md border text-[10px] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${u.is_active
                          ? "border-emerald-500/30 text-emerald-400 hover:bg-red-500/5 hover:text-red-400 hover:border-red-500/30"
                          : "border-red-500/30 text-red-400 hover:bg-emerald-500/5 hover:text-emerald-400 hover:border-emerald-500/30"
                          }`}
                        title={isSelf ? "Cannot suspend yourself" : u.is_active ? "Suspend user" : "Reactivate user"}
                      >
                        {isSavingActive ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : u.is_active ? (
                          <UserCheck className="h-3 w-3" />
                        ) : (
                          <UserX className="h-3 w-3" />
                        )}
                        {u.is_active ? "Active" : "Suspended"}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── AUDIT LOG TAB ── */}
      {tab === "audit" && (
        <Card>
          <CardHeader className="pb-2 pt-4 px-5">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Audit Log
                {auditTotal > 0 && (
                  <span className="text-[10px] text-muted-foreground font-normal">({auditTotal.toLocaleString()} entries)</span>
                )}
              </CardTitle>
              <div className="flex items-center gap-2 flex-wrap">
                {/* User filter */}
                <select
                  value={auditUser}
                  onChange={(e) => setAuditUser(e.target.value)}
                  className="h-7 px-2 rounded-md bg-muted/30 border border-border/40 text-[10px] max-w-[160px]"
                >
                  <option value="">All Users</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>{u.name || u.email.split("@")[0]}</option>
                  ))}
                </select>
                {/* Action filter */}
                <select
                  value={auditAction}
                  onChange={(e) => setAuditAction(e.target.value)}
                  className="h-7 px-2 rounded-md bg-muted/30 border border-border/40 text-[10px]"
                >
                  <option value="">All Actions</option>
                  {Object.entries(ACTION_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
                <button
                  onClick={() => loadAudit(1)}
                  disabled={auditLoading}
                  className="flex items-center gap-1 h-7 px-2.5 rounded-md bg-primary/10 text-primary text-[10px] font-medium hover:bg-primary/20 transition-colors disabled:opacity-50"
                >
                  {auditLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Filter className="h-3 w-3" />}
                  Filter
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-4">
            {auditLoading ? (
              <div className="space-y-1.5">
                {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-10 rounded bg-muted/20 animate-pulse" />)}
              </div>
            ) : auditLogs.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">No audit log entries found.</p>
            ) : (
              <>
                {/* Table header */}
                <div className="grid grid-cols-[1fr_100px_100px_90px] gap-2 px-2 pb-1 border-b border-border/20 mb-1">
                  {["Action / Details", "User", "IP Address", "Time"].map((h) => (
                    <span key={h} className="text-[9px] text-muted-foreground/60 font-medium uppercase tracking-wide">{h}</span>
                  ))}
                </div>
                <div className="space-y-0.5">
                  {auditLogs.map((log) => {
                    const actor = users.find((u) => u.id === log.user_id);
                    const actionLabel = ACTION_LABELS[log.action] || log.action;
                    const hasDetails = Object.keys(log.details || {}).length > 0;
                    return (
                      <div
                        key={log.id}
                        className="grid grid-cols-[1fr_100px_100px_90px] gap-2 px-2 py-1.5 rounded hover:bg-muted/20 transition-colors items-start"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${log.action === "login" ? "bg-emerald-500/10 text-emerald-400" :
                              log.action === "logout" ? "bg-slate-500/10 text-slate-400" :
                                log.action.includes("delete") ? "bg-red-500/10 text-red-400" :
                                  log.action.includes("create") || log.action.includes("trigger") ? "bg-blue-500/10 text-blue-400" :
                                    "bg-amber-500/10 text-amber-400"
                              }`}>
                              {actionLabel}
                            </span>
                            {log.resource_type && (
                              <span className="text-[9px] text-muted-foreground/50">{log.resource_type}{log.resource_id ? ` #${log.resource_id.slice(0, 8)}` : ""}</span>
                            )}
                          </div>
                          {hasDetails && (
                            <p className="text-[9px] text-muted-foreground/40 mt-0.5 truncate">
                              {Object.entries(log.details).slice(0, 2).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                            </p>
                          )}
                        </div>
                        <div className="text-[10px] text-muted-foreground truncate">
                          {actor ? (actor.name || actor.email.split("@")[0]) : (log.user_id ? log.user_id.slice(0, 8) + "…" : "System")}
                        </div>
                        <div className="text-[10px] text-muted-foreground/50 font-mono truncate">
                          {log.ip_address || "—"}
                        </div>
                        <div className="text-[10px] text-muted-foreground/50" title={new Date(log.created_at).toLocaleString()}>
                          {timeAgo(log.created_at)}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Pagination */}
                {auditPages > 1 && (
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/20">
                    <span className="text-[10px] text-muted-foreground">
                      Page {auditPage} of {auditPages}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        disabled={auditPage <= 1 || auditLoading}
                        onClick={() => loadAudit(auditPage - 1)}
                        className="h-6 px-2 text-[10px] rounded border border-border/40 hover:bg-muted/40 disabled:opacity-40 transition-colors"
                      >
                        ← Prev
                      </button>
                      <button
                        disabled={auditPage >= auditPages || auditLoading}
                        onClick={() => loadAudit(auditPage + 1)}
                        className="h-6 px-2 text-[10px] rounded border border-border/40 hover:bg-muted/40 disabled:opacity-40 transition-colors"
                      >
                        Next →
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
