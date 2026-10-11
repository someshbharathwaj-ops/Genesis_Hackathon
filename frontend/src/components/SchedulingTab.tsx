"use client";

import React, { useEffect, useState } from "react";
import {
  Calendar,
  CheckCircle2,
  Clock,
  Hourglass,
  Lock,
  Play,
  RefreshCw,
  Sparkles,
  TrendingDown,
} from "lucide-react";
import {
  CourseResponse,
  RetentionSessionPlanResponse,
  ReviewQueueResponse,
  ScheduledAssessmentResponse,
  UserResponse,
} from "../types";
import { recallApi } from "../lib/api-client";

interface SchedulingTabProps {
  course: CourseResponse | null;
  currentUser: UserResponse | null;
  onStartRetentionSession?: (plan: RetentionSessionPlanResponse) => void;
}

export function SchedulingTab({
  course,
  currentUser,
  onStartRetentionSession,
}: SchedulingTabProps) {
  const [queue, setQueue] = useState<ReviewQueueResponse | null>(null);
  const [courseAssessments, setCourseAssessments] = useState<ScheduledAssessmentResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Retention Session Planning
  const [isPlanning, setIsPlanning] = useState<boolean>(false);
  const [plannedPlan, setPlannedPlan] = useState<RetentionSessionPlanResponse | null>(null);

  const fetchQueue = async () => {
    if (!course || !currentUser) return;
    setLoading(true);
    setError(null);
    try {
      const [q, assessments] = await Promise.all([
        recallApi.getReviewQueue(course.id, currentUser.id).catch(() => null),
        recallApi.listCourseAssessments(course.id).catch(() => []),
      ]);
      setQueue(q);
      setCourseAssessments(assessments || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load review queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [course?.id, currentUser?.id]);

  const handlePlanRetentionSession = async () => {
    if (!course || !currentUser) return;
    setIsPlanning(true);
    try {
      const plan = await recallApi.planRetentionSession(course.id, currentUser.id, 5);
      setPlannedPlan(plan);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to plan retention session.");
    } finally {
      setIsPlanning(false);
    }
  };

  if (!currentUser) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <Calendar className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">Please log in to view spaced retention review queue.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="tactile-card p-12 text-center text-ink-muted flex flex-col items-center gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-brand-yellow" />
        <span className="font-bold text-sm">Evaluating exponential retention decay curves and Rule 6 boundaries...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Scheduling Header */}
      <section className="tactile-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-yellow text-ink">SPACED RETENTION ENGINE</span>
            <span className="text-xs font-bold text-ink-muted">Rule 6 Working-Memory Guard</span>
          </div>
          <h2 className="text-2xl font-black text-ink">Spaced Retention & Review Queues</h2>
          <p className="text-sm text-ink-muted mt-1 max-w-2xl font-medium">
            Models retention decay R(t) = exp(-Δt / S) and enforces Rule 6: items tested within 1 hour
            are locked in working memory and disqualified from durable retention reviews.
          </p>
        </div>

        <button
          onClick={handlePlanRetentionSession}
          disabled={isPlanning}
          className="tactile-btn-yellow text-xs py-2 px-4"
        >
          <Sparkles className={`w-3.5 h-3.5 ${isPlanning ? "animate-spin" : ""}`} />
          <span>{isPlanning ? "Planning..." : "Plan Spaced Session (≤ 5 Qs)"}</span>
        </button>
      </section>

      {/* Persisted Course Assessment Calendar (Quizzes & Tests) */}
      <section className="tactile-card p-6 bg-surface flex flex-col gap-4 border-2 border-ink shadow-hard">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-ink/10 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="tactile-tag bg-brand-coral text-white text-[10px] font-black uppercase">
                EXAM &amp; QUIZ CALENDAR
              </span>
              <span className="text-xs font-bold text-ink-muted">
                Course: {course?.code || "CS340"}
              </span>
            </div>
            <h3 className="text-lg font-black text-ink mt-0.5">
              Teacher-Scheduled Quizzes &amp; Assessments
            </h3>
          </div>
          <span className="text-xs font-bold text-ink-muted">
            {courseAssessments.length} Scheduled Assessment{courseAssessments.length === 1 ? "" : "s"}
          </span>
        </div>

        {courseAssessments.length === 0 ? (
          <div className="p-6 text-center text-ink-muted bg-surface-warm/40 border border-ink/10 rounded-friendly-sm">
            <Clock className="w-6 h-6 mx-auto mb-1 text-ink-faint" />
            <p className="text-xs font-bold">No upcoming quizzes scheduled yet by your instructor.</p>
            <p className="text-[11px] font-medium text-ink-muted mt-0.5">
              When instructors post an exam or test, it automatically appears here and alerts your notification center.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {courseAssessments.map((a) => (
              <div
                key={a.id}
                className="p-4 bg-white border-2 border-ink rounded-friendly-sm shadow-hard-sm flex flex-col justify-between gap-3"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="tactile-tag bg-brand-coral text-white text-[10px] uppercase font-black">
                      {a.status}
                    </span>
                    <span className="text-xs font-bold text-ink-muted flex items-center gap-1">
                      <Clock className="w-3 h-3 text-brand-coral" />
                      <span>{a.duration_minutes} Minutes</span>
                    </span>
                  </div>
                  <h4 className="text-sm font-black text-ink leading-snug">{a.title}</h4>
                  {a.description && (
                    <p className="text-xs text-ink-muted mt-1 leading-relaxed">{a.description}</p>
                  )}
                </div>

                <div className="pt-2 border-t border-ink/10 flex items-center justify-between gap-2">
                  <div className="text-[11px] font-bold text-ink">
                    <span className="text-ink-muted block text-[10px]">SCHEDULED TIME</span>
                    {new Date(a.scheduled_at).toLocaleString()}
                  </div>
                  {onStartRetentionSession && (
                    <button
                      onClick={() => handlePlanRetentionSession()}
                      className="tactile-btn-yellow text-xs py-1 px-2.5 font-black shrink-0"
                    >
                      Prepare Now
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Queue Stat Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="tactile-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold text-ink-muted">
            <span>Total Queue Objectives</span>
            <Calendar className="w-4 h-4 text-brand-cyan" />
          </div>
          <div className="text-3xl font-black text-ink mt-2">
            {queue?.total_objectives_evaluated ?? queue?.total_queue_items ?? 0}
          </div>
          <div className="text-[11px] text-ink-muted font-medium mt-1">
            Active objectives in course
          </div>
        </div>

        <div className="tactile-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold text-ink-muted">
            <span>Overdue Retention Items</span>
            <TrendingDown className="w-4 h-4 text-brand-coral" />
          </div>
          <div className="text-3xl font-black text-brand-coral mt-2">
            {queue?.overdue_count ?? queue?.overdue_items_count ?? 0}
          </div>
          <div className="text-[11px] text-ink-muted font-medium mt-1">
            Estimated Retention R(t) &lt; 0.70
          </div>
        </div>

        <div className="tactile-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-bold text-ink-muted">
            <span>Working-Memory Locked (Rule 6)</span>
            <Lock className="w-4 h-4 text-brand-yellow" />
          </div>
          <div className="text-3xl font-black text-ink mt-2">
            {queue?.working_memory_locked_count ?? queue?.locked_items_count ?? 0}
          </div>
          <div className="text-[11px] text-ink-muted font-medium mt-1">
            Under 1 hour cooldown boundary
          </div>
        </div>
      </section>

      {/* Main Review Queue Table & Plan Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Spaced Review Queue */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-ink flex items-center gap-2">
              <Clock className="w-5 h-5 text-brand-yellow" />
              <span>Prioritized Spaced Review Queue</span>
            </h3>
            <button onClick={fetchQueue} className="tactile-btn-white text-xs py-1 px-2.5">
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
                    <th className="p-3">Estimated R(t)</th>
                    <th className="p-3">Stability</th>
                    <th className="p-3">Rule 6 Status</th>
                    <th className="p-3">Urgency Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y border-ink/10 font-medium">
                  {queue?.items?.map((item) => {
                    const isLocked = item.in_working_memory ?? item.is_working_memory_locked ?? false;
                    const stability = item.retention_stability_days ?? item.stability_days ?? 0;
                    const urgency = item.urgency_score ?? item.review_priority ?? 0;
                    const titleText = item.objective_title || item.title || "";

                    return (
                      <tr key={item.objective_id} className="hover:bg-surface-warm/20">
                        <td className="p-3">
                          <div className="font-black text-ink">{item.objective_code}</div>
                          {titleText && <div className="text-[10px] text-ink-muted">{titleText}</div>}
                        </td>
                        <td className="p-3 font-mono font-bold text-ink">
                          {((item.estimated_retention ?? 0) * 100).toFixed(1)}%
                        </td>
                        <td className="p-3 font-mono text-ink">
                          {stability.toFixed(1)}d
                        </td>
                        <td className="p-3">
                          {isLocked ? (
                            <span className="tactile-tag bg-brand-coral/20 text-brand-coral text-[9px] py-0 px-1.5 uppercase font-bold">
                              <Lock className="w-2.5 h-2.5 inline mr-1" />
                              Working Memory Cooldown
                            </span>
                          ) : (
                            <span className="tactile-tag bg-brand-green/20 text-brand-green text-[9px] py-0 px-1.5 uppercase font-bold">
                              <CheckCircle2 className="w-2.5 h-2.5 inline mr-1" />
                              Retention Eligible
                            </span>
                          )}
                        </td>
                        <td className="p-3 font-mono text-ink font-bold">
                          {urgency.toFixed(2)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Retention Session Plan */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <h3 className="text-lg font-black text-ink flex items-center gap-2">
            <Hourglass className="w-5 h-5 text-brand-cyan" />
            <span>Session Plan Inspector</span>
          </h3>

          {plannedPlan ? (() => {
            const planItems = plannedPlan.planned_items || (plannedPlan as any).planned_questions || [];
            const contextName = plannedPlan.context || plannedPlan.assessment_context || "retention_review";
            const totalCount = plannedPlan.total_items ?? (plannedPlan as any).total_questions ?? planItems.length;
            const reasonText = plannedPlan.reason || (plannedPlan as any).rationale || "";

            return (
              <div className="tactile-card p-5 flex flex-col gap-4">
                <div className="flex items-center justify-between pb-2 border-b border-ink/10">
                  <span className="tactile-tag bg-brand-yellow text-ink text-xs uppercase">
                    {contextName.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs font-bold text-ink-muted">
                    Bounded &le; {totalCount} Items
                  </span>
                </div>

                {reasonText && (
                  <div className="text-xs text-ink font-medium leading-relaxed">
                    <strong>Plan Reason:</strong> {reasonText}
                  </div>
                )}

                <div className="flex flex-col gap-2 pt-2 border-t border-ink/10">
                  <div className="text-xs font-bold text-ink">Planned Retention Items:</div>
                  {planItems.map((q: any, idx: number) => (
                    <div
                      key={q.objective_id || q.question_id || idx}
                      className="p-3 bg-surface-warm/40 border border-ink rounded text-xs flex items-center justify-between"
                    >
                      <div>
                        <span className="font-bold text-ink mr-2">#{idx + 1}</span>
                        <span className="font-mono text-[11px] text-brand-cyan mr-1 font-bold">
                          [{q.objective_code}]
                        </span>
                        <span className="text-ink font-medium">
                          {q.objective_title || q.title || "Retention Target"}
                        </span>
                      </div>
                      <span className="tactile-tag bg-surface text-ink text-[9px] py-0 px-1 uppercase">
                        {q.urgency_classification || q.difficulty || "due"}
                      </span>
                    </div>
                  ))}
                </div>

                {onStartRetentionSession && (
                  <button
                    onClick={() => onStartRetentionSession(plannedPlan)}
                    className="tactile-btn-yellow text-xs py-2 w-full mt-2 font-black"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Begin Spaced Retention Retest</span>
                  </button>
                )}
              </div>
            );
          })() : (
            <div className="tactile-card p-12 text-center text-ink-muted flex flex-col items-center justify-center gap-2 min-h-[280px]">
              <Calendar className="w-8 h-8 text-ink-faint" />
              <div className="font-bold text-sm">No Active Retention Plan</div>
              <p className="text-xs max-w-xs font-medium">
                Click &quot;Plan Spaced Session&quot; above to generate a bounded retention review
                session respecting Rule 6 cooldown boundaries.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
