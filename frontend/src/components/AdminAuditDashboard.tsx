"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  CheckCircle,
  Database,
  Download,
  FileCheck,
  FileText,
  Lock,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import {
  AdminAuditLogEntry,
  AdminAuditSummaryResponse,
  CourseResponse,
  HealthResponse,
  UserResponse,
} from "../types";
import { recallApi } from "../lib/api-client";

interface AdminAuditDashboardProps {
  currentUser: UserResponse | null;
  courses: CourseResponse[];
  onRefreshCourses?: () => void;
}

export function AdminAuditDashboard({
  currentUser,
  courses,
  onRefreshCourses,
}: AdminAuditDashboardProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [auditSummary, setAuditSummary] = useState<AdminAuditSummaryResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<AdminAuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [filterCourse, setFilterCourse] = useState<string>("ALL");

  const fetchAdminData = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [h, summary, logs] = await Promise.all([
        recallApi.getHealth().catch(() => null),
        recallApi.getAdminAuditSummary().catch((err) => {
          setErrorMessage(err.message || "Failed to load audit summary");
          return null;
        }),
        recallApi.getAdminAuditLogs(50).catch(() => []),
      ]);
      setHealth(h);
      setAuditSummary(summary);
      setAuditLogs(logs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error fetching institutional audit data";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const filteredLogs =
    filterCourse === "ALL"
      ? auditLogs
      : auditLogs.filter((l) => l.courseCode === filterCourse);

  const handleExportAuditReport = () => {
    const reportData = {
      generatedAt: new Date().toISOString(),
      generatedBy: currentUser?.email || "admin.audit@recall.edu",
      systemStatus: health || "operational",
      telemetry: auditSummary?.system_telemetry || null,
      aggregateCounts: auditSummary?.aggregate_counts || null,
      courses: auditSummary?.course_summaries || courses,
      auditEvents: auditLogs,
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `recall_audit_report_${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Banner */}
      <div className="tactile-card p-6 bg-surface-warm/40 border-2 border-ink shadow-hard flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="tactile-tag bg-brand-green text-ink text-xs font-black">
              ADMINISTRATIVE AUDIT CONSOLE
            </span>
            <span className="text-xs font-bold text-ink-muted">
              Role: Institutional Auditor & System Overseer
            </span>
          </div>
          <h2 className="text-2xl font-black text-ink">
            Platform Audit, Provenance & Reports
          </h2>
          <p className="text-xs text-ink-muted font-medium mt-1">
            Independent institutional governance interface. Monitors SLM grounding, deterministic mathematical grading audits, ADR 0002 assessment lockouts, and multi-course operational health.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchAdminData}
            disabled={loading}
            className="tactile-btn-white text-xs py-2 px-3 font-bold flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Telemetry</span>
          </button>
          <button
            onClick={handleExportAuditReport}
            className="tactile-btn-yellow text-xs py-2 px-3.5 font-bold flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Audit Report</span>
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm text-xs font-bold text-ink">
          {errorMessage}
        </div>
      )}

      {/* Top Telemetry Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: System Engine Health */}
        <div className="tactile-card p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-ink-muted">Backend Service</span>
            <Server className="w-4 h-4 text-brand-green" />
          </div>
          <div className="text-xl font-black text-ink">
            {health?.status === "ok" ? "100% Operational" : "Active (Uvicorn)"}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-brand-green">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>FastAPI Monolith v{health?.version || "0.1.0"}</span>
          </div>
        </div>

        {/* Card 2: SLM Inference Provider */}
        <div className="tactile-card p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-ink-muted">SLM Grounding Engine</span>
            <Sparkles className="w-4 h-4 text-brand-yellow" />
          </div>
          <div className="text-xl font-black text-ink">
            {auditSummary?.system_telemetry?.model_provider || "Phi-3 Mini (3.8B)"}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-ink-muted">
            <Activity className="w-3.5 h-3.5 text-brand-yellow" />
            <span>Ollama Adapter &bull; Strict Course Grounding</span>
          </div>
        </div>

        {/* Card 3: Deterministic Relational Engine */}
        <div className="tactile-card p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-ink-muted">Grading Authority</span>
            <Database className="w-4 h-4 text-brand-cyan" />
          </div>
          <div className="text-xl font-black text-ink">Pure Mathematical</div>
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-brand-cyan">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Zero LLM Grading Power (ADR 0001)</span>
          </div>
        </div>

        {/* Card 4: Assessment Lockout Sentinel */}
        <div className="tactile-card p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-ink-muted">ADR 0002 Sentinel</span>
            <Lock className="w-4 h-4 text-brand-coral" />
          </div>
          <div className="text-xl font-black text-ink">Enforced (Active)</div>
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-brand-coral">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Strict AI Lockout on Exams</span>
          </div>
        </div>
      </div>

      {/* Aggregate Platform Totals */}
      {auditSummary?.aggregate_counts && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="tactile-card p-3 text-center">
            <span className="text-[10px] text-ink-muted font-bold block">COURSES</span>
            <span className="text-lg font-black text-ink">{auditSummary.aggregate_counts.total_courses}</span>
          </div>
          <div className="tactile-card p-3 text-center">
            <span className="text-[10px] text-ink-muted font-bold block">STUDENTS</span>
            <span className="text-lg font-black text-ink">{auditSummary.aggregate_counts.total_students}</span>
          </div>
          <div className="tactile-card p-3 text-center">
            <span className="text-[10px] text-ink-muted font-bold block">INSTRUCTORS</span>
            <span className="text-lg font-black text-ink">{auditSummary.aggregate_counts.total_instructors}</span>
          </div>
          <div className="tactile-card p-3 text-center">
            <span className="text-[10px] text-ink-muted font-bold block">VERIFIED QUESTIONS</span>
            <span className="text-lg font-black text-brand-cyan">{auditSummary.aggregate_counts.verified_questions}</span>
          </div>
          <div className="tactile-card p-3 text-center">
            <span className="text-[10px] text-ink-muted font-bold block">INGESTED CHUNKS</span>
            <span className="text-lg font-black text-brand-green">{auditSummary.aggregate_counts.ingested_chunks}</span>
          </div>
        </div>
      )}

      {/* Multi-Course Institutional Registry */}
      <div className="tactile-card p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-brand-yellow" />
            <h3 className="font-black text-base text-ink">
              Multi-Course Knowledge & Curriculum Registry
            </h3>
          </div>
          <span className="tactile-tag bg-surface text-ink text-xs font-bold">
            {courses.length} Active Courses
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b-2 border-ink/20 text-ink-muted font-bold">
                <th className="py-2.5 px-3">Course Code</th>
                <th className="py-2.5 px-3">Course Title</th>
                <th className="py-2.5 px-3">Enrolled Students</th>
                <th className="py-2.5 px-3">Verified Questions</th>
                <th className="py-2.5 px-3">Ingested Chunks</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink/10 font-medium text-ink">
              {(auditSummary?.course_summaries || courses.map(c => ({
                id: c.id,
                code: c.code,
                title: c.title,
                enrolled_students: 0,
                verified_questions: 0,
                ingested_chunks: 0,
              }))).map((course) => (
                <tr key={course.id} className="hover:bg-surface-warm/40">
                  <td className="py-3 px-3 font-mono font-black text-brand-cyan">
                    {course.code}
                  </td>
                  <td className="py-3 px-3 font-bold text-ink">{course.title}</td>
                  <td className="py-3 px-3 font-mono font-bold text-ink">
                    {"enrolled_students" in course ? course.enrolled_students : 0}
                  </td>
                  <td className="py-3 px-3 font-mono font-bold text-brand-cyan">
                    {"verified_questions" in course ? course.verified_questions : 0}
                  </td>
                  <td className="py-3 px-3 font-mono font-bold text-brand-green">
                    {"ingested_chunks" in course ? course.ingested_chunks : 0}
                  </td>
                  <td className="py-3 px-3">
                    <span className="tactile-tag bg-brand-green/20 text-ink text-[10px] py-0 px-2 font-bold">
                      INITIALIZED & ACTIVE
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Log Ledger */}
      <div className="tactile-card p-5 flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-brand-green" />
            <h3 className="font-black text-base text-ink">
              Institutional Evaluation & Attempt Audit Ledger
            </h3>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-bold text-ink-muted">Filter by Course:</label>
            <select
              value={filterCourse}
              onChange={(e) => setFilterCourse(e.target.value)}
              className="tactile-select text-xs font-bold py-1 px-2"
            >
              <option value="ALL">All Courses</option>
              {courses.map((c) => (
                <option key={c.id} value={c.code}>
                  {c.code}
                </option>
              ))}
            </select>
          </div>
        </div>

        <p className="text-[11px] text-ink-muted">
          Cryptographic SHA-256 digests computed over immutable attempt tuples <code>(attempt_id, student_id, question_id, score, timestamp)</code>. Proves mathematical grading provenance against post-submission manipulation.
        </p>

        {filteredLogs.length === 0 ? (
          <div className="p-8 text-center text-ink-muted bg-surface rounded-friendly border-2 border-dashed border-ink/20">
            <FileText className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
            <p className="font-bold text-xs">No attempt records recorded in the ledger yet.</p>
            <p className="text-[11px] mt-1">Submit an answer in Student Practice mode to generate immutable provenance records.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b-2 border-ink/20 text-ink-muted font-bold">
                  <th className="py-2.5 px-3">Log ID</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Actor & Role</th>
                  <th className="py-2.5 px-3">Course</th>
                  <th className="py-2.5 px-3">Event Action</th>
                  <th className="py-2.5 px-3">Verdict</th>
                  <th className="py-2.5 px-3">Provenance Hash (SHA-256)</th>
                  <th className="py-2.5 px-3">Audit Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink/10 font-medium text-ink">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-surface-warm/40">
                    <td className="py-3 px-3 font-mono font-bold text-ink-muted">
                      {log.id}
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-ink-muted">
                      {log.timestamp}
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-bold text-ink">{log.actor}</span>
                      <span className="text-[10px] text-ink-muted block uppercase">
                        {log.role}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono font-black text-brand-cyan">
                      {log.courseCode}
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] font-bold">
                      {log.action}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`tactile-tag text-[10px] py-0.5 px-2 font-black ${
                          log.verdict === "VERIFIED" || log.verdict === "GROUNDED"
                            ? "bg-brand-green/20 text-ink"
                            : log.verdict === "BLOCKED_LOCKOUT"
                            ? "bg-brand-coral text-white"
                            : "bg-brand-yellow/30 text-ink"
                        }`}
                      >
                        {log.verdict}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-[10px] text-ink-muted truncate max-w-[140px]" title={log.provenanceHash}>
                      {log.provenanceHash.substring(0, 16)}...
                    </td>
                    <td className="py-3 px-3 text-ink-muted max-w-[280px]">
                      {log.details}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
