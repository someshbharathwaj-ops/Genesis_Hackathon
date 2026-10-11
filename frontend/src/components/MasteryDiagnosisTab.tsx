"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle2,
  Clock,
  Compass,
  HelpCircle,
  Play,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import {
  CourseDiagnosticSummaryResponse,
  CourseMasterySummaryResponse,
  CourseResponse,
  DiagnosticSessionPlanResponse,
  UserResponse,
} from "../types";
import { recallApi } from "../lib/api-client";

interface MasteryDiagnosisTabProps {
  course: CourseResponse | null;
  currentUser: UserResponse | null;
  onStartProbingPlan?: (plan: DiagnosticSessionPlanResponse) => void;
  onWriteTest?: () => void;
  preparationNotice?: string | null;
  onClearPreparationNotice?: () => void;
}

export function MasteryDiagnosisTab({
  course,
  currentUser,
  onStartProbingPlan,
  onWriteTest,
  preparationNotice,
  onClearPreparationNotice,
}: MasteryDiagnosisTabProps) {
  const [masterySummary, setMasterySummary] = useState<CourseMasterySummaryResponse | null>(null);
  const [diagnosticSummary, setDiagnosticSummary] = useState<CourseDiagnosticSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Probing Session Planning
  const [targetObjectiveId, setTargetObjectiveId] = useState<string>("");
  const [plannedSession, setPlannedSession] = useState<DiagnosticSessionPlanResponse | null>(null);
  const [isPlanning, setIsPlanning] = useState<boolean>(false);

  const fetchMasteryAndDiagnosis = async () => {
    if (!course || !currentUser) return;
    setLoading(true);
    setError(null);
    try {
      const [mSummary, dSummary] = await Promise.all([
        recallApi.getStudentCourseMastery(currentUser.id, course.id),
        recallApi.getStudentCourseDiagnosis(currentUser.id, course.id),
      ]);
      setMasterySummary(mSummary);
      setDiagnosticSummary(dSummary);
      if (mSummary.objectives.length > 0 && !targetObjectiveId) {
        setTargetObjectiveId(mSummary.objectives[0].objective_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load mastery data";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMasteryAndDiagnosis();
  }, [course?.id, currentUser?.id]);

  const handlePlanSession = async () => {
    if (!course || !currentUser || !targetObjectiveId) return;
    setIsPlanning(true);
    try {
      const plan = await recallApi.planDiagnosticSession(
        currentUser.id,
        course.id,
        targetObjectiveId
      );
      setPlannedSession(plan);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to generate diagnostic plan.");
    } finally {
      setIsPlanning(false);
    }
  };

  if (!currentUser) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <Brain className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">Please log in to view student mastery and diagnostic traces.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="tactile-card p-12 text-center text-ink-muted flex flex-col items-center gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-brand-yellow" />
        <span className="font-bold text-sm">Evaluating deterministic mastery and evidence ledgers...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Diagnostic Retest Notice if arriving from Tutor Preparation */}
      {preparationNotice && (
        <div className="tactile-card border-brand-yellow bg-brand-yellow/15 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-in shadow-hard">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-friendly-sm bg-brand-yellow text-ink border-2 border-ink flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="font-black text-sm text-ink flex items-center gap-2">
                <span>Diagnostic Retest Mode</span>
                <span className="tactile-tag bg-brand-yellow text-ink text-[10px] uppercase font-black">
                  Review &amp; Test
                </span>
              </div>
              <p className="text-xs text-ink-muted font-medium mt-0.5">
                {preparationNotice}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {onWriteTest && (
              <button
                type="button"
                onClick={onWriteTest}
                className="tactile-btn-yellow text-xs py-2 px-4 font-black flex items-center gap-1.5 shadow-hard-sm hover:scale-[1.02] transition-transform"
              >
                <span>✍️ Write Test Now</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
            {onClearPreparationNotice && (
              <button
                type="button"
                onClick={onClearPreparationNotice}
                className="tactile-btn-white text-xs py-2 px-3 font-bold"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}

      {/* Overview Stat Cards */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="tactile-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold text-ink-muted">
            <span>Course Performance Index</span>
            <TrendingUp className="w-4 h-4 text-brand-green" />
          </div>
          <div className="text-3xl font-black text-ink mt-2">
            {masterySummary
              ? `${((masterySummary.average_performance ?? masterySummary.course_mastery_index ?? 0) * 100).toFixed(0)}%`
              : "0%"}
          </div>
          <div className="text-[11px] text-ink-muted font-medium mt-1">
            Deterministic Bayesian Knowledge Model
          </div>
        </div>

        <div className="tactile-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold text-ink-muted">
            <span>Mastered Objectives</span>
            <CheckCircle2 className="w-4 h-4 text-brand-green" />
          </div>
          <div className="text-3xl font-black text-brand-green mt-2">
            {masterySummary?.mastered_count || 0}
            <span className="text-sm text-ink-muted font-bold">
              {" "}/ {masterySummary?.total_objectives || 0}
            </span>
          </div>
          <div className="text-[11px] text-ink-muted font-medium mt-1">
            Performance ≥ 0.85 Verified Threshold
          </div>
        </div>

        <div className="tactile-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold text-ink-muted">
            <span>Identified Gaps</span>
            <AlertTriangle className="w-4 h-4 text-brand-coral" />
          </div>
          <div className="text-3xl font-black text-brand-coral mt-2">
            {diagnosticSummary?.demonstrated_weakness_count ??
              diagnosticSummary?.confirmed_gap_count ??
              diagnosticSummary?.identified_root_cause_gaps?.length ??
              0}
          </div>
          <div className="text-[11px] text-ink-muted font-medium mt-1">
            Evidence-backed root cause gaps
          </div>
        </div>

        <div className="tactile-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold text-ink-muted">
            <span>Untested / Incomplete</span>
            <HelpCircle className="w-4 h-4 text-brand-cyan" />
          </div>
          <div className="text-3xl font-black text-ink mt-2">
            {(diagnosticSummary?.untested_count || 0) +
              (diagnosticSummary?.insufficient_evidence_count || 0)}
          </div>
          <div className="text-[11px] text-ink-muted font-medium mt-1">
            Requiring diagnostic probes
          </div>
        </div>
      </section>

      {/* Root Cause Gaps / Prerequisite Alerts (if any) */}
      {diagnosticSummary &&
        ((diagnosticSummary.prerequisite_failures && diagnosticSummary.prerequisite_failures.length > 0) ||
          (diagnosticSummary.identified_root_cause_gaps && diagnosticSummary.identified_root_cause_gaps.length > 0)) && (
          <div className="tactile-card-warm border-brand-coral bg-brand-coral/10 p-5 flex flex-col gap-2">
            <div className="flex items-center gap-2 font-black text-sm text-brand-coral">
              <AlertTriangle className="w-4 h-4" />
              <span>CURRICULUM PREREQUISITE GAPS DETECTED</span>
            </div>
            <p className="text-xs text-ink font-medium">
              Recall identified foundational gap objectives that require intervention:
            </p>
            <div className="flex flex-wrap gap-2 mt-1">
              {diagnosticSummary.prerequisite_failures?.map((pf, idx) => (
                <span key={idx} className="tactile-tag bg-white text-ink text-xs">
                  <span className="font-bold text-brand-coral">{pf.target_code}</span> requires{" "}
                  <span className="font-bold text-brand-green">{pf.unmet_prerequisite_code}</span>
                </span>
              ))}
              {diagnosticSummary.identified_root_cause_gaps?.map((gap, idx) => (
                <span key={`gap-${idx}`} className="tactile-tag bg-brand-coral text-white text-xs font-bold">
                  Gap: {gap}
                </span>
              ))}
            </div>
          </div>
        )}

      {/* Main Breakdown: Objective Mastery & Diagnostic Status */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Objective Mastery Ledger Table */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-ink flex items-center gap-2">
              <Brain className="w-5 h-5 text-brand-yellow" />
              <span>Objective Mastery & Confidence Bounds</span>
            </h3>
            <button
              onClick={fetchMasteryAndDiagnosis}
              className="tactile-btn-white text-xs py-1 px-2.5"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Refresh</span>
            </button>
          </div>

          <div className="tactile-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-warm/60 border-b-2 border-ink text-ink font-black">
                  <tr>
                    <th className="p-3">Objective</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Performance</th>
                    <th className="p-3">Confidence</th>
                    <th className="p-3">Attempts</th>
                  </tr>
                </thead>
                <tbody className="divide-y border-ink/10 font-medium">
                  {masterySummary?.objectives?.map((obj) => {
                    const mState = obj.mastery_state || obj.status || "untested";
                    const statusTag =
                      mState === "mastered"
                        ? "bg-brand-green text-ink"
                        : mState === "developing"
                        ? "bg-brand-yellow text-ink"
                        : mState === "needs_remediation"
                        ? "bg-brand-coral text-white"
                        : "bg-surface-muted text-ink-muted";

                    const perf = obj.performance_score ?? obj.mastery_probability ?? 0;
                    const conf = obj.confidence_score ?? obj.confidence_bound_lower ?? 0;
                    const attempts = obj.total_attempts ?? obj.attempts_count ?? 0;

                    return (
                      <tr key={obj.objective_id} className="hover:bg-surface-warm/20">
                        <td className="p-3">
                          <div className="font-black text-ink">{obj.objective_code}</div>
                          {obj.blocked_by_prerequisites && obj.blocked_by_prerequisites.length > 0 && (
                            <div className="text-[10px] text-brand-coral font-bold">
                              Blocked: {obj.blocked_by_prerequisites.join(", ")}
                            </div>
                          )}
                        </td>
                        <td className="p-3">
                          <span className={`tactile-tag text-[9px] py-0 px-1.5 ${statusTag} uppercase`}>
                            {mState.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="p-3 font-mono font-bold text-ink">
                          {(perf * 100).toFixed(1)}%
                        </td>
                        <td className="p-3 font-mono text-ink">
                          {(conf * 100).toFixed(0)}%
                        </td>
                        <td className="p-3 font-mono text-ink">{attempts}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Bounded Diagnostic Probing Session Planner */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <h3 className="text-lg font-black text-ink flex items-center gap-2">
            <Compass className="w-5 h-5 text-brand-coral" />
            <span>Diagnostic Session Planner</span>
          </h3>

          <div className="tactile-card p-5 flex flex-col gap-4">
            <div>
              <div className="font-black text-sm text-ink">Generate Bounded Diagnostic Plan</div>
              <p className="text-xs text-ink-muted mt-1 font-medium">
                Select a learning objective to generate a bounded sequence of strictly ≤ 5 diagnostic
                probing questions.
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold text-ink">Target Objective:</label>
              <select
                value={targetObjectiveId}
                onChange={(e) => setTargetObjectiveId(e.target.value)}
                className="tactile-input text-xs font-bold"
              >
                {masterySummary?.objectives?.map((obj) => (
                  <option key={obj.objective_id} value={obj.objective_id}>
                    {obj.objective_code} ({obj.mastery_state || obj.status || "untested"})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handlePlanSession}
              disabled={isPlanning || !targetObjectiveId}
              className="tactile-btn-yellow text-xs py-2 w-full"
            >
              <Compass className={`w-3.5 h-3.5 ${isPlanning ? "animate-spin" : ""}`} />
              <span>{isPlanning ? "Planning Session..." : "Generate Diagnostic Plan (≤ 5 Qs)"}</span>
            </button>

            {/* Generated Plan Details */}
            {plannedSession && (() => {
              const questions = plannedSession.recommended_questions || plannedSession.planned_questions || [];
              const rationaleText = plannedSession.session_rationale || plannedSession.rationale || "";
              const count = questions.length;

              return (
                <div className="mt-2 p-4 bg-surface-warm/40 border-2 border-ink rounded-friendly-sm flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="tactile-tag bg-brand-green text-ink text-[10px]">
                      {count} Questions Planned
                    </span>
                    <span className="text-[10px] font-bold text-ink-muted uppercase">
                      Bounded &le; 5 Qs
                    </span>
                  </div>

                  {rationaleText && (
                    <div className="text-xs text-ink font-medium">
                      <strong>Rationale:</strong> {rationaleText}
                    </div>
                  )}

                  <div className="flex flex-col gap-2 pt-2 border-t border-ink/10">
                    {questions.map((pq, idx) => (
                      <div
                        key={pq.question_id}
                        className="p-2 bg-white border border-ink rounded text-xs flex items-center justify-between"
                      >
                        <div>
                          <span className="font-bold text-ink mr-2">#{idx + 1}</span>
                          <span className="font-medium text-ink">{pq.title}</span>
                        </div>
                        <span className="tactile-tag bg-surface-muted text-ink text-[9px] py-0 px-1 uppercase">
                          {pq.difficulty}
                        </span>
                      </div>
                    ))}
                  </div>

                  {onStartProbingPlan && (
                    <button
                      onClick={() => onStartProbingPlan(plannedSession)}
                      className="tactile-btn-coral text-xs py-1.5 w-full mt-1"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Begin Diagnostic Probes</span>
                    </button>
                  )}
                </div>
              );
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}
