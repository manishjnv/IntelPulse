"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Loading } from "@/components/Loading";
import { Modal } from "@/components/Modal";
import { Pagination } from "@/components/Pagination";
import { StatCard } from "@/components/StatCard";
import { useToast } from "@/components/Toast";
import {
  getCases,
  getCaseStats,
  createCase,
  deleteCase,
  updateCase,
  cloneCase,
  getCaseAssignees,
  bulkUpdateCaseStatus,
  bulkDeleteCases,
  bulkAssignCases,
  getCaseExportUrl,
} from "@/lib/api";
import type {
  Case,
  CaseListResponse,
  CaseStats,
  CaseStatus,
  CasePriority,
  CaseType,
  CaseCreate,
  Severity,
  Assignee,
} from "@/types";
import { ALLOWED_TRANSITIONS } from "@/types";
import {
  Briefcase,
  Plus,
  Filter,
  RefreshCw,
  Search,
  ChevronRight,
  AlertTriangle,
  Clock,
  CheckCircle,
  Pause,
  XCircle,
  Shield,
  Crosshair,
  HelpCircle,
  Trash2,
  X,
  Download,
  CheckSquare,
  Square,
  Users,
  Copy,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Calendar,
  Bookmark,
  Eye,
} from "lucide-react";

/* ── Config Maps (module-level, not re-created each render) ── */

const STATUS_CONFIG: Record<CaseStatus, { label: string; color: string; icon: React.ElementType; shape: string }> = {
  new: { label: "New", color: "bg-blue-500/10 text-blue-400 border-blue-500/20", icon: Clock, shape: "●" },
  in_progress: { label: "In Progress", color: "bg-amber-500/10 text-amber-400 border-amber-500/20", icon: RefreshCw, shape: "◆" },
  pending: { label: "Pending", color: "bg-purple-500/10 text-purple-400 border-purple-500/20", icon: Pause, shape: "■" },
  resolved: { label: "Resolved", color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", icon: CheckCircle, shape: "▲" },
  closed: { label: "Closed", color: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20", icon: XCircle, shape: "▬" },
};

const PRIORITY_CONFIG: Record<CasePriority, { label: string; color: string; shape: string }> = {
  critical: { label: "Critical", color: "text-red-400 bg-red-500/10 border-red-500/20", shape: "▲▲" },
  high: { label: "High", color: "text-orange-400 bg-orange-500/10 border-orange-500/20", shape: "▲" },
  medium: { label: "Medium", color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20", shape: "◆" },
  low: { label: "Low", color: "text-blue-400 bg-blue-500/10 border-blue-500/20", shape: "▽" },
};

const TYPE_CONFIG: Record<CaseType, { label: string; icon: React.ElementType }> = {
  incident_response: { label: "Incident Response", icon: AlertTriangle },
  investigation: { label: "Investigation", icon: Search },
  hunt: { label: "Threat Hunt", icon: Crosshair },
  rfi: { label: "Request for Info", icon: HelpCircle },
};

const SEVERITY_STYLES: Record<string, { color: string; shape: string }> = {
  critical: { color: "text-red-400", shape: "⬤" },
  high: { color: "text-orange-400", shape: "◆" },
  medium: { color: "text-yellow-400", shape: "■" },
  low: { color: "text-blue-400", shape: "▽" },
  info: { color: "text-cyan-400", shape: "○" },
};

const PRIORITY_BAR_COLORS: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-blue-500",
};

const SORTABLE_COLUMNS: { key: string; label: string }[] = [
  { key: "updated_at", label: "Updated" },
  { key: "created_at", label: "Created" },
  { key: "title", label: "Title" },
  { key: "priority", label: "Priority" },
  { key: "status", label: "Status" },
  { key: "severity", label: "Severity" },
];

const SAVED_VIEWS: { key: string; label: string; icon: React.ElementType; filters: Record<string, string> }[] = [
  { key: "open", label: "Open Cases", icon: Briefcase, filters: {} },
  { key: "critical_high", label: "Critical/High", icon: AlertTriangle, filters: { priority: "critical,high" } },
  { key: "active", label: "Active", icon: RefreshCw, filters: { status: "in_progress" } },
  { key: "pending", label: "Pending", icon: Pause, filters: { status: "pending" } },
  { key: "incidents", label: "Incidents", icon: Shield, filters: { case_type: "incident_response" } },
  { key: "hunts", label: "Hunts", icon: Crosshair, filters: { case_type: "hunt" } },
];

/* ── Create Modal ─────────────────────────────────────── */

function CreateCaseModal({
  open,
  onClose,
  onCreated,
  assignees,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  assignees: Assignee[];
}) {
  const { toast } = useToast();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [caseType, setCaseType] = useState<CaseType>("investigation");
  const [priority, setPriority] = useState<CasePriority>("medium");
  const [severity, setSeverity] = useState<Severity>("medium");
  const [tlp, setTlp] = useState("TLP:GREEN");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [assigneeId, setAssigneeId] = useState("");
  const [saving, setSaving] = useState(false);

  const addTag = () => {
    const t = tagInput.trim().toLowerCase();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await createCase({
        title: title.trim(),
        description: description.trim() || undefined,
        case_type: caseType,
        priority,
        severity,
        tlp,
        tags: tags.length > 0 ? tags : undefined,
        assignee_id: assigneeId || undefined,
      });
      setTitle("");
      setDescription("");
      setCaseType("investigation");
      setPriority("medium");
      setSeverity("medium");
      setTlp("TLP:GREEN");
      setTags([]);
      setAssigneeId("");
      toast("Case created successfully", "success");
      onCreated();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create case";
      toast(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} ariaLabel="Create new case" className="w-full max-w-lg">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary" />
            New Case
          </h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label="Close dialog">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Title *</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Case title..."
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary min-h-[80px]"
              placeholder="Describe the case..."
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Type</label>
              <select
                value={caseType}
                onChange={(e) => setCaseType(e.target.value as CaseType)}
                className="w-full mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {Object.entries(TYPE_CONFIG).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as CasePriority)}
                className="w-full mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                  <option key={k} value={k}>{v.shape} {v.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value as Severity)}
                className="w-full mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {Object.entries(SEVERITY_STYLES).map(([k, v]) => (
                  <option key={k} value={k}>{v.shape} {k.charAt(0).toUpperCase() + k.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">TLP</label>
              <select
                value={tlp}
                onChange={(e) => setTlp(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="TLP:RED">TLP:RED</option>
                <option value="TLP:AMBER+STRICT">TLP:AMBER+STRICT</option>
                <option value="TLP:AMBER">TLP:AMBER</option>
                <option value="TLP:GREEN">TLP:GREEN</option>
                <option value="TLP:CLEAR">TLP:CLEAR</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Tags</label>
            <div className="flex gap-2 mt-1">
              <input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
                placeholder="Add tag and press Enter"
                className="flex-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <Button type="button" variant="ghost" size="sm" onClick={addTag} disabled={!tagInput.trim()}>Add</Button>
            </div>
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {tags.map((t) => (
                  <Badge key={t} variant="outline" className="text-[10px] px-1.5 py-0 bg-muted/50 cursor-pointer hover:bg-destructive/10" onClick={() => setTags(tags.filter((x) => x !== t))}>
                    {t} <X className="h-2.5 w-2.5 ml-0.5" />
                  </Badge>
                ))}
              </div>
            )}
          </div>
          {assignees.length > 0 && (
            <div>
              <label className="text-xs font-medium text-muted-foreground">Assignee</label>
              <select
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
                className="w-full mt-1 px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">Unassigned</option>
                {assignees.map((a) => (
                  <option key={a.id} value={a.id}>{a.name || a.email}</option>
                ))}
              </select>
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={saving || !title.trim()}>
              {saving ? "Creating..." : "Create Case"}
            </Button>
          </div>
        </form>
    </Modal>
  );
}

/* ── Inner Page (uses useSearchParams) ────────────────── */

function CasesPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const [cases, setCases] = useState<Case[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(() => parseInt(searchParams.get("page") || "1", 10));
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<CaseStats | null>(null);
  const [assignees, setAssignees] = useState<Assignee[]>([]);

  const [showFilters, setShowFilters] = useState(() => {
    return !!(searchParams.get("status") || searchParams.get("priority") || searchParams.get("case_type") || searchParams.get("severity") || searchParams.get("tlp") || searchParams.get("tag") || searchParams.get("search"));
  });
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "");
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get("priority") || "");
  const [typeFilter, setTypeFilter] = useState(searchParams.get("case_type") || "");
  const [severityFilter, setSeverityFilter] = useState(searchParams.get("severity") || "");
  const [tlpFilter, setTlpFilter] = useState(searchParams.get("tlp") || "");
  const [tagFilter, setTagFilter] = useState(searchParams.get("tag") || "");
  const [searchTerm, setSearchTerm] = useState(searchParams.get("search") || "");
  const [sortBy, setSortBy] = useState(searchParams.get("sort_by") || "updated_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">((searchParams.get("sort_order") as "asc" | "desc") || "desc");
  const [showCreate, setShowCreate] = useState(false);
  const [dateFrom, setDateFrom] = useState(searchParams.get("date_from") || "");
  const [dateTo, setDateTo] = useState(searchParams.get("date_to") || "");
  const [assigneeFilter, setAssigneeFilter] = useState(searchParams.get("assignee_id") || "");
  const [activeView, setActiveView] = useState(searchParams.get("view") || "");

  // Bulk selection
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkAction, setBulkAction] = useState("");
  const [bulkAssignee, setBulkAssignee] = useState("");

  // Sync filters → URL query params
  const syncUrl = useCallback((overrides: Record<string, string | number> = {}) => {
    const params = new URLSearchParams();
    const vals: Record<string, string> = {
      status: statusFilter,
      priority: priorityFilter,
      case_type: typeFilter,
      severity: severityFilter,
      tlp: tlpFilter,
      tag: tagFilter,
      search: searchTerm,
      date_from: dateFrom,
      date_to: dateTo,
      assignee_id: assigneeFilter,
      view: activeView,
      sort_by: sortBy,
      sort_order: sortOrder,
      ...Object.fromEntries(Object.entries(overrides).map(([k, v]) => [k, String(v)])),
    };
    const pg = overrides.page ?? page;
    if (Number(pg) > 1) vals.page = String(pg);
    if (vals.sort_by === "updated_at") delete vals.sort_by;
    if (vals.sort_order === "desc") delete vals.sort_order;

    for (const [k, v] of Object.entries(vals)) {
      if (v) params.set(k, v);
    }
    const qs = params.toString();
    router.replace(`/cases${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [statusFilter, priorityFilter, typeFilter, severityFilter, tlpFilter, tagFilter, searchTerm, dateFrom, dateTo, assigneeFilter, activeView, sortBy, sortOrder, page, router]);

  const fetchData = useCallback(
    async (p = 1) => {
      setLoading(true);
      try {
        const [res, st] = await Promise.all([
          getCases({
            page: p,
            page_size: 20,
            status: statusFilter || undefined,
            priority: priorityFilter || undefined,
            case_type: typeFilter || undefined,
            search: searchTerm || undefined,
            severity: severityFilter || undefined,
            tlp: tlpFilter || undefined,
            tag: tagFilter || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
            assignee_id: assigneeFilter || undefined,
            sort_by: sortBy,
            sort_order: sortOrder,
          }),
          getCaseStats(),
        ]);
        setCases(res.cases);
        setTotal(res.total);
        setPage(res.page);
        setPages(res.pages);
        setStats(st);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load cases";
        toast(msg, "error");
      } finally {
        setLoading(false);
      }
    },
    [statusFilter, priorityFilter, typeFilter, searchTerm, severityFilter, tlpFilter, tagFilter, dateFrom, dateTo, assigneeFilter, sortBy, sortOrder, toast]
  );

  useEffect(() => {
    fetchData(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyFilters = (p = 1) => {
    syncUrl({ page: p });
    fetchData(p);
  };

  useEffect(() => {
    getCaseAssignees().then(setAssignees).catch(() => {});
  }, []);

  const handlePageChange = (p: number) => {
    syncUrl({ page: p });
    fetchData(p);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const clearFilters = () => {
    setStatusFilter("");
    setPriorityFilter("");
    setTypeFilter("");
    setSeverityFilter("");
    setTlpFilter("");
    setTagFilter("");
    setSearchTerm("");
    setDateFrom("");
    setDateTo("");
    setAssigneeFilter("");
    setActiveView("");
    setSortBy("updated_at");
    setSortOrder("desc");
    router.replace("/cases", { scroll: false });
    setTimeout(() => fetchData(1), 0);
  };

  const handleSort = (col: string) => {
    let newOrder: "asc" | "desc" = "desc";
    if (sortBy === col) {
      newOrder = sortOrder === "desc" ? "asc" : "desc";
    }
    setSortBy(col);
    setSortOrder(newOrder);
    syncUrl({ sort_by: col, sort_order: newOrder, page: 1 });
    setLoading(true);
    getCases({
      page: 1,
      page_size: 20,
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
      case_type: typeFilter || undefined,
      search: searchTerm || undefined,
      severity: severityFilter || undefined,
      tlp: tlpFilter || undefined,
      tag: tagFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      assignee_id: assigneeFilter || undefined,
      sort_by: col,
      sort_order: newOrder,
    }).then((res) => {
      setCases(res.cases);
      setTotal(res.total);
      setPage(res.page);
      setPages(res.pages);
    }).catch((err: unknown) => {
      const msg = err instanceof Error ? err.message : "Sort failed";
      toast(msg, "error");
    }).finally(() => setLoading(false));
  };

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === cases.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(cases.map((c) => c.id)));
    }
  };

  const handleBulkAction = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0 || !bulkAction) return;
    try {
      if (bulkAction === "delete") {
        if (!confirm(`Delete ${ids.length} case(s)?`)) return;
        const res = await bulkDeleteCases(ids);
        toast(`Deleted ${res.deleted} case(s)`, "success");
      } else if (bulkAction === "assign" && bulkAssignee) {
        const res = await bulkAssignCases(ids, bulkAssignee);
        toast(`Assigned ${res.updated} case(s)`, "success");
      } else if (["new", "in_progress", "pending", "resolved", "closed"].includes(bulkAction)) {
        const res = await bulkUpdateCaseStatus(ids, bulkAction as CaseStatus);
        toast(`Updated status on ${res.updated} case(s)`, "success");
      }
      setSelected(new Set());
      setBulkAction("");
      setBulkAssignee("");
      fetchData(page);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Bulk operation failed";
      toast(msg, "error");
      fetchData(page);
    }
  };

  const handleExport = (format: "json" | "csv") => {
    const ids = selected.size > 0 ? Array.from(selected) : undefined;
    window.open(getCaseExportUrl(format, ids), "_blank");
    toast(`Export started (${format.toUpperCase()})`, "info");
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this case?")) return;
    try {
      await deleteCase(id);
      toast("Case deleted", "success");
      fetchData(page);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete case";
      toast(msg, "error");
    }
  };

  const handleClone = async (id: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const cloned = await cloneCase(id);
      toast(`Cloned: ${cloned.title}`, "success");
      fetchData(page);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to clone case";
      toast(msg, "error");
    }
  };


  const handleViewSelect = (viewKey: string) => {
    const view = SAVED_VIEWS.find((v) => v.key === viewKey);
    if (!view) return;
    setActiveView(viewKey);
    setStatusFilter(view.filters.status || "");
    setPriorityFilter(view.filters.priority || "");
    setTypeFilter(view.filters.case_type || "");
    setSeverityFilter(view.filters.severity || "");
    setTlpFilter(view.filters.tlp || "");
    setTagFilter(view.filters.tag || "");
    setSearchTerm(view.filters.search || "");
    setDateFrom(view.filters.date_from || "");
    setDateTo(view.filters.date_to || "");
    setAssigneeFilter(view.filters.assignee_id || "");
    setLoading(true);
    getCases({
      page: 1,
      page_size: 20,
      status: view.filters.status || undefined,
      priority: view.filters.priority || undefined,
      case_type: view.filters.case_type || undefined,
      search: view.filters.search || undefined,
      severity: view.filters.severity || undefined,
      tlp: view.filters.tlp || undefined,
      tag: view.filters.tag || undefined,
      date_from: view.filters.date_from || undefined,
      date_to: view.filters.date_to || undefined,
      assignee_id: view.filters.assignee_id || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    }).then((res) => {
      setCases(res.cases);
      setTotal(res.total);
      setPage(res.page);
      setPages(res.pages);
    }).catch((err: unknown) => {
      const msg = err instanceof Error ? err.message : "View load failed";
      toast(msg, "error");
    }).finally(() => setLoading(false));
    syncUrl({ view: viewKey, page: 1 });
  };

  const handleInlineEdit = async (caseId: string, field: string, value: string, e: React.ChangeEvent<HTMLSelectElement>) => {
    e.stopPropagation();
    try {
      await updateCase(caseId, { [field]: value });
      setCases((prev) => prev.map((c) => c.id === caseId ? { ...c, [field]: value } : c));
      toast(`Updated ${field}`, "success");
      getCaseStats().then(setStats).catch(() => {});
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to update ${field}`;
      toast(msg, "error");
    }
  };
  if (loading && cases.length === 0) return <Loading />;

  return (
    <div className="space-y-4 pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Briefcase className="h-5 w-5 text-primary" />
            Cases
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {total} case{total !== 1 ? "s" : ""} total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="text-xs"
          >
            <Filter className="h-3.5 w-3.5 mr-1" />
            Filters
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchData(page)}
            className="text-xs"
            title="Refresh"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleExport("csv")}
            className="text-xs"
            title="Export CSV"
          >
            <Download className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)} className="text-xs">
            <Plus className="h-3.5 w-3.5 mr-1" />
            New Case
          </Button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard title="Total Cases" value={stats.total_cases} icon={<Briefcase className="h-4 w-4" />} />
          <StatCard title="Open Cases" value={stats.open_cases} icon={<Clock className="h-4 w-4" />} />
          <StatCard title="Critical Priority" value={stats.by_priority?.critical || 0} icon={<AlertTriangle className="h-4 w-4" />} />
          <StatCard title="Closed (7d)" value={stats.recent_closed} icon={<CheckCircle className="h-4 w-4" />} />
        </div>
      )}


      {/* Saved Views */}
      <div className="flex items-center gap-2 px-1 flex-wrap">
        <span className="text-[10px] text-muted-foreground uppercase font-medium flex items-center gap-1">
          <Bookmark className="h-3 w-3" /> Views:
        </span>
        {SAVED_VIEWS.map((view) => {
          const isActive = activeView === view.key;
          const ViewIcon = view.icon;
          return (
            <button
              key={view.key}
              onClick={() => { if (isActive) { clearFilters(); } else { handleViewSelect(view.key); } }}
              className={`text-[10px] px-2 py-0.5 rounded-md border transition-colors flex items-center gap-1 ${
                isActive
                  ? "bg-primary/10 border-primary/30 text-primary font-medium"
                  : "border-border/40 text-muted-foreground hover:text-foreground hover:border-border"
              }`}
            >
              <ViewIcon className="h-3 w-3" />
              {view.label}
            </button>
          );
        })}
      </div>
      {/* Filters */}
      {showFilters && (
        <Card>
          <CardContent className="p-3">
            <div className="flex flex-wrap gap-3 items-end">
              <div className="flex-1 min-w-[160px]">
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Search</label>
                <div className="relative mt-1">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <input
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && applyFilters(1)}
                    placeholder="Search cases..."
                    className="w-full pl-7 pr-3 py-1.5 rounded-md bg-muted/50 border border-border text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>
              <div>
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                >
                  <option value="">All</option>
                  {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                    <option key={k} value={k}>{v.shape} {v.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Priority</label>
                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                >
                  <option value="">All</option>
                  {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                    <option key={k} value={k}>{v.shape} {v.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Type</label>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                >
                  <option value="">All</option>
                  {Object.entries(TYPE_CONFIG).map(([k, v]) => (
                    <option key={k} value={k}>{v.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Severity</label>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                >
                  <option value="">All</option>
                  {Object.entries(SEVERITY_STYLES).map(([k, v]) => (
                    <option key={k} value={k}>{v.shape} {k.charAt(0).toUpperCase() + k.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-muted-foreground uppercase">TLP</label>
                <select
                  value={tlpFilter}
                  onChange={(e) => setTlpFilter(e.target.value)}
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                >
                  <option value="">All</option>
                  <option value="TLP:RED">TLP:RED</option>
                  <option value="TLP:AMBER+STRICT">TLP:AMBER+STRICT</option>
                  <option value="TLP:AMBER">TLP:AMBER</option>
                  <option value="TLP:GREEN">TLP:GREEN</option>
                  <option value="TLP:CLEAR">TLP:CLEAR</option>
                </select>
              </div>
              <div className="min-w-[120px]">
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Tag</label>
                <input
                  value={tagFilter}
                  onChange={(e) => setTagFilter(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && applyFilters(1)}
                  placeholder="e.g. ransomware"
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                />
              </div>
              <div>
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Date From</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                />
              </div>
              <div>
                <label className="text-[10px] font-medium text-muted-foreground uppercase">Date To</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                />
              </div>
              {assignees.length > 0 && (
                <div>
                  <label className="text-[10px] font-medium text-muted-foreground uppercase">Assignee</label>
                  <select
                    value={assigneeFilter}
                    onChange={(e) => setAssigneeFilter(e.target.value)}
                    className="mt-1 block w-full px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                  >
                    <option value="">All</option>
                    {assignees.map((a) => (
                      <option key={a.id} value={a.id}>{a.name || a.email}</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex gap-2 items-end">
                <Button size="sm" className="text-xs" onClick={() => applyFilters(1)}>Apply</Button>
                <Button variant="ghost" size="sm" className="text-xs" onClick={clearFilters}>Clear</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sort Bar */}
      <div className="flex items-center gap-2 px-1 flex-wrap">
        <span className="text-[10px] text-muted-foreground uppercase font-medium flex items-center gap-1">
          <ArrowUpDown className="h-3 w-3" /> Sort:
        </span>
        {SORTABLE_COLUMNS.map((col) => {
          const isActive = sortBy === col.key;
          return (
            <button
              key={col.key}
              onClick={() => handleSort(col.key)}
              className={`text-[10px] px-2 py-0.5 rounded-md border transition-colors ${
                isActive
                  ? "bg-primary/10 border-primary/30 text-primary font-medium"
                  : "border-border/40 text-muted-foreground hover:text-foreground hover:border-border"
              }`}
            >
              {col.label}
              {isActive && (
                sortOrder === "desc"
                  ? <ArrowDown className="h-2.5 w-2.5 ml-0.5 inline" />
                  : <ArrowUp className="h-2.5 w-2.5 ml-0.5 inline" />
              )}
            </button>
          );
        })}
      </div>

      {/* Bulk Action Bar */}
      {selected.size > 0 && (
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs font-medium">{selected.size} selected</span>
              <select
                value={bulkAction}
                onChange={(e) => setBulkAction(e.target.value)}
                className="px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
              >
                <option value="">Bulk action...</option>
                <optgroup label="Set Status">
                  <option value="new">→ New</option>
                  <option value="in_progress">→ In Progress</option>
                  <option value="pending">→ Pending</option>
                  <option value="resolved">→ Resolved</option>
                  <option value="closed">→ Closed</option>
                </optgroup>
                <option value="assign">Assign to...</option>
                <option value="delete">Delete</option>
              </select>
              {bulkAction === "assign" && (
                <select
                  value={bulkAssignee}
                  onChange={(e) => setBulkAssignee(e.target.value)}
                  className="px-2 py-1.5 rounded-md bg-muted/50 border border-border text-xs"
                >
                  <option value="">Select user...</option>
                  {assignees.map((a) => (
                    <option key={a.id} value={a.id}>{a.name || a.email}</option>
                  ))}
                </select>
              )}
              <Button
                size="sm"
                className="text-xs"
                onClick={handleBulkAction}
                disabled={!bulkAction || (bulkAction === "assign" && !bulkAssignee)}
              >
                Apply
              </Button>
              <Button variant="ghost" size="sm" className="text-xs" onClick={() => { setSelected(new Set()); setBulkAction(""); }}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Case List */}
      <div className="space-y-2">
        {cases.length > 0 && (
          <div className="flex items-center gap-2 px-1">
            <button onClick={toggleSelectAll} className="text-muted-foreground hover:text-foreground" aria-label="Select all cases">
              {selected.size === cases.length ? <CheckSquare className="h-4 w-4" /> : <Square className="h-4 w-4" />}
            </button>
            <span className="text-[10px] text-muted-foreground">Select all</span>
          </div>
        )}
        {cases.map((c) => {
          const statusCfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.new;
          const priorityCfg = PRIORITY_CONFIG[c.priority] || PRIORITY_CONFIG.medium;
          const typeCfg = TYPE_CONFIG[c.case_type] || TYPE_CONFIG.investigation;
          const sevStyle = SEVERITY_STYLES[c.severity] || SEVERITY_STYLES.medium;
          const StatusIcon = statusCfg.icon;
          const TypeIcon = typeCfg.icon;

          return (
            <Card
              key={c.id}
              className="hover:border-primary/40 cursor-pointer transition-all group"
              onClick={() => router.push(`/cases/${c.id}`)}
            >
              <CardContent className="p-3">
                <div className="flex items-start gap-3">
                  <button
                    onClick={(e) => toggleSelect(c.id, e)}
                    className="mt-0.5 text-muted-foreground hover:text-foreground shrink-0"
                    aria-label={`Select case ${c.title}`}
                  >
                    {selected.has(c.id) ? <CheckSquare className="h-4 w-4 text-primary" /> : <Square className="h-4 w-4" />}
                  </button>

                  {/* Priority indicator — shape + color for colorblind safety */}
                  <div className="mt-0.5 flex flex-col items-center gap-0.5 shrink-0" title={`Priority: ${priorityCfg.label}`}>
                    <div className={`w-1.5 h-10 rounded-full ${PRIORITY_BAR_COLORS[c.priority] || "bg-blue-500"}`} />
                    <span className="text-[8px] font-bold leading-none select-none" aria-hidden="true">{priorityCfg.shape}</span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-semibold truncate group-hover:text-primary transition-colors">
                        {c.title}
                      </h3>
                      <div onClick={(e) => e.stopPropagation()}>
                        <select
                          value={c.status}
                          onChange={(e) => handleInlineEdit(c.id, "status", e.target.value, e)}
                          className={`text-[10px] px-1.5 py-0.5 rounded-md border appearance-none cursor-pointer ${statusCfg.color}`}
                          title="Change status"
                        >
                          <option value={c.status}>{statusCfg.shape} {statusCfg.label}</option>
                          {(ALLOWED_TRANSITIONS[c.status] || []).filter((s: CaseStatus) => s !== c.status).map((s: CaseStatus) => {
                            const cfg = STATUS_CONFIG[s];
                            return <option key={s} value={s}>{cfg.shape} {cfg.label}</option>;
                          })}
                        </select>
                      </div>
                      <div onClick={(e) => e.stopPropagation()}>
                        <select
                          value={c.priority}
                          onChange={(e) => handleInlineEdit(c.id, "priority", e.target.value, e)}
                          className={`text-[10px] px-1.5 py-0.5 rounded-md border appearance-none cursor-pointer ${priorityCfg.color}`}
                          title="Change priority"
                        >
                          {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
                            <option key={k} value={k}>{v.shape} {v.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {c.description && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{c.description}</p>
                    )}

                    <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <TypeIcon className="h-3 w-3" />
                        {typeCfg.label}
                      </span>
                      <span className={`flex items-center gap-0.5 ${sevStyle.color}`}>
                        <span aria-hidden="true">{sevStyle.shape}</span>
                        {c.severity}
                      </span>
                      {c.linked_intel_count > 0 && <span>{c.linked_intel_count} intel</span>}
                      {c.linked_ioc_count > 0 && <span>{c.linked_ioc_count} IOC{c.linked_ioc_count > 1 ? "s" : ""}</span>}
                      <span>{new Date(c.updated_at).toLocaleDateString()}</span>
                      {c.owner_email && <span className="truncate max-w-[100px]" title={c.owner_email}>{c.owner_email.split('@')[0]}</span>}
                      {c.assignee_email && <span className="truncate max-w-[120px]">→ {c.assignee_email}</span>}
                    </div>

                    {c.tags.length > 0 && (
                      <div className="flex gap-1 mt-1.5 flex-wrap">
                        {c.tags.slice(0, 5).map((t) => (
                          <Badge key={t} variant="outline" className="text-[9px] px-1 py-0 bg-muted/50">{t}</Badge>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={(e) => handleClone(c.id, c.title, e)}
                      className="p-1 rounded hover:bg-blue-500/10 text-muted-foreground hover:text-blue-400 transition-colors opacity-0 group-hover:opacity-100"
                      title="Clone case"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(c.id, e)}
                      className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                      title="Delete case"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}

        {cases.length === 0 && !loading && (
          <Card>
            <CardContent className="p-8 text-center">
              <Briefcase className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No cases yet</p>
              <p className="text-xs text-muted-foreground/60 mt-1">Create your first case to start tracking incidents</p>
              <Button size="sm" className="mt-3 text-xs" onClick={() => setShowCreate(true)}>
                <Plus className="h-3.5 w-3.5 mr-1" /> New Case
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {pages > 1 && <Pagination page={page} pages={pages} onPageChange={handlePageChange} />}

      <CreateCaseModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={() => fetchData(1)}
        assignees={assignees}
      />
    </div>
  );
}

/* ── Exported Page (Suspense boundary for useSearchParams) */

export default function CasesPage() {
  return (
    <Suspense fallback={<Loading />}>
      <CasesPageInner />
    </Suspense>
  );
}
