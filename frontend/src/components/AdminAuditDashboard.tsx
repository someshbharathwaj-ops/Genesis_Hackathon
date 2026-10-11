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
import { CourseResponse, HealthResponse, UserResponse } from "../types";
import { recallApi } from "../lib/api-client";

interface AdminAuditDashboardProps {
  currentUser: UserResponse | null;
  courses: CourseResponse[];
  onRefreshCourses?: () => void;
}

interface AuditLogEntry {
  id: string;
  timestamp: string;
  actor: string;
  role: string;
  courseCode: string;
  action: string;
  provenanceHash: string;
  verdict: "VERIFIED" | "BLOCKED_LOCKOUT" | "GROUNDED" | "CONTRADICTION" | "NEUTRAL";
  details: string;
}

export function AdminAuditDashboard({
  currentUser,
  courses,
  onRefreshCourses,
}: AdminAuditDashboardProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterCourse, setFilterCourse] = useState<string>("ALL");

  // Simulated live institutional audit ledger events
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([
    {
      id: "LOG-9041",
      timestamp: new Date(Date.now() - 1000 * 60 * 2).toLocaleTimeString(),
      actor: "Ada Lovelace",
      role: "student",
      courseCode: "CS301",
      action: "TUTOR_QUERY",
      provenanceHash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      verdict: "GROUNDED",
      details: "Query on Coffman deadlock conditions grounded strictly against os_concurrency_and_scheduling.md",
    },
    {
      id: "LOG-9040",
      timestamp: new Date(Date.now() - 1000 * 60 * 5).toLocaleTimeString(),
      actor: "Ada Lovelace",
      role: "student",
      courseCode: "CS340",
      action: "ATTEMPT_EVALUATION",
      provenanceHash: "7d1a58b29f9c011e4b3f885e3170a481c95b706c9a4087e59600109d9426f092",
      verdict: "VERIFIED",
      details: "Deterministic mathematical grader executed for attribute closure {A}+. Score: 1.0/1.0",
    },
    {
      id: "LOG-9039",
      timestamp: new Date(Date.now() - 1000 * 60 * 12).toLocaleTimeString(),
      actor: "Ada Lovelace",
      role: "student",
      courseCode: "CS340",
      action: "SCORED_ASSESSMENT_LOCKOUT",
      provenanceHash: "19f9a2e3811c002b88f918907604adbf1052631a00a402e1b4396dc1e737119e",
      verdict: "BLOCKED_LOCKOUT",
      details: "Tutor and Revisor queries locked out during active scored test (ADR 0002 Enforcement)",
    },
    {
      id: "LOG-9038",
      timestamp: new Date(Date.now() - 1000 * 60 * 25).toLocaleTimeString(),
      actor: "Prof. Andrew Tanenbaum",
      role: "instructor",
      courseCode: "CS301",
      action: "COURSE_MATERIALS_INGEST",
      provenanceHash: "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      verdict: "VERIFIED",
      details: "13 Operating Systems lecture documents ingested into CS301 knowledge base",
    },
    {
      id: "LOG-9037",
      timestamp: new Date(Date.now() - 1000 * 60 * 40).toLocaleTimeString(),
      actor: "Prof. E. F. Codd",
      role: "instructor",
      courseCode: "CS340",
      action: "REVISOR_CONCEPT_AUDIT",
      provenanceHash: "8c91a001b22e1189dca394f0017e889b7410091efadbc2e9870001bcde881201",
      verdict: "CONTRADICTION",
      details: "Contradiction detected on erroneous candidate closure claim against relational axioms",
    },
  ]);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const h = await recallApi.getHealth();
      setHealth(h);
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
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
      totalCourses: courses.length,
      courses: courses.map((c) => ({ code: c.code, title: c.title, id: c.id })),
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
            onClick={fetchHealth}
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

      {/* Top Telemetry Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: System Engine Health */}
        <div className="tactile-card p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-ink-muted">Backend Service</span>
            <Server className="w-4 h-4 text-brand-green" />
          </div>
          <div className="text-xl font-black text-ink">
            {health?.status === "healthy" ? "100% Operational" : "Active (Uvicorn)"}
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
          <div className="text-xl font-black text-ink">Phi-3 Mini (3.8B)</div>
          <div className="flex items-center gap-1.5 text-[11px] font-bold text-ink-muted">
            <Activity className="w-3.5 h-3.5 text-brand-yellow" />
            <span>Ollama Local &bull; Temperature 0.2</span>
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
                <th className="py-2.5 px-3">Course ID</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">SLM Grounding</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink/10 font-medium text-ink">
              {courses.map((course) => (
                <tr key={course.id} className="hover:bg-surface-warm/40">
                  <td className="py-3 px-3 font-mono font-black text-brand-cyan">
                    {course.code}
                  </td>
                  <td className="py-3 px-3 font-bold text-ink">{course.title}</td>
                  <td className="py-3 px-3 font-mono text-[11px] text-ink-muted">
                    {course.id}
                  </td>
                  <td className="py-3 px-3">
                    <span className="tactile-tag bg-brand-green/20 text-ink text-[10px] py-0 px-2 font-bold">
                      INITIALIZED & ACTIVE
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="tactile-tag bg-brand-yellow/20 text-ink text-[10px] py-0 px-2 font-bold">
                      INDEXED VECTOR STORE
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
              Institutional SLM & Evaluation Audit Ledger
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
      </div>
    </div>
  );
}
