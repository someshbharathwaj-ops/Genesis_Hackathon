"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  FileCheck2,
  Layers,
  Lock,
  SearchCheck,
  Send,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { CourseResponse, RevisorReviewResponse, UserResponse } from "../types";
import { ApiError, recallApi } from "../lib/api-client";

interface RevisorTabProps {
  course: CourseResponse | null;
  currentUser: UserResponse | null;
  hasActiveScoredAssessment: boolean;
}

export function RevisorTab({
  course,
  currentUser,
  hasActiveScoredAssessment,
}: RevisorTabProps) {
  const [candidateText, setCandidateText] = useState<string>(
    "Given R(A, B, C, D) with F = {A -> B, B -> C}, attribute closure {A}+ includes {A, B, C} via transitivity."
  );
  const [queryTopic, setQueryTopic] = useState<string>("Transitive functional dependencies");
  const [checkDeterministicLogic, setCheckDeterministicLogic] = useState<boolean>(true);

  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [reviewResult, setReviewResult] = useState<RevisorReviewResponse | null>(null);
  const [lockoutError, setLockoutError] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleRunAudit = async () => {
    if (!course || !currentUser || !candidateText.trim()) return;

    if (hasActiveScoredAssessment) {
      setLockoutError(
        "Revisor evidence reviews are locked out while an active scored assessment is in progress (ADR 0002)."
      );
      setReviewResult(null);
      return;
    }

    setIsAuditing(true);
    setLockoutError(null);
    setErrorMsg(null);
    setReviewResult(null);

    try {
      const resp = await recallApi.reviewExplanation(
        course.id,
        currentUser.id,
        candidateText,
        queryTopic,
        undefined,
        checkDeterministicLogic
      );
      setReviewResult(resp);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.problem.code === "ASSESSMENT_LOCKOUT") {
        setLockoutError(err.problem.detail);
      } else {
        setErrorMsg(err instanceof Error ? err.message : "Revisor audit failed.");
      }
    } finally {
      setIsAuditing(false);
    }
  };

  const setSampleClaim = (type: "valid" | "contradiction" | "ungrounded") => {
    if (type === "valid") {
      setCandidateText(
        "Given R(A, B, C, D) with F = {A -> B, B -> C}, attribute closure {A}+ includes {A, B, C} via transitivity."
      );
      setQueryTopic("Transitive functional dependencies");
    } else if (type === "contradiction") {
      setCandidateText(
        "Given R(A, B, C) with dependencies A -> B and B -> C, the attribute closure of {A}+ does not contain {B} or {C}."
      );
      setQueryTopic("Attribute closure contradiction");
    } else {
      setCandidateText(
        "In quantum relational database systems, qubits replace classical primary keys to optimize Bell states."
      );
      setQueryTopic("Quantum databases");
    }
  };

  if (!course) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <BookOpen className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">Select a course to run Revisor adversarial audits.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Revisor Header */}
      <section className="tactile-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-coral text-white">SLM ROLE B</span>
            <span className="text-xs font-bold text-ink-muted">Adversarial Evidence Reviewer</span>
          </div>
          <h2 className="text-2xl font-black text-ink">Grounded Revisor & Adversarial Audits</h2>
          <p className="text-sm text-ink-muted mt-1 max-w-2xl font-medium">
            Cross-examines student claims, tutor explanations, or misconceptions against authoritative syllabus
            citations. Overrides generative consensus whenever deterministic relational contradictions exist.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="tactile-tag bg-brand-green text-ink text-xs">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>ADR 0002 Authority</span>
          </span>
        </div>
      </section>

      {/* Lockout Warning */}
      {(hasActiveScoredAssessment || lockoutError) && (
        <div className="tactile-card border-brand-coral bg-brand-coral/15 p-6 flex items-start gap-4 animate-shake">
          <div className="w-10 h-10 rounded-friendly-sm bg-brand-coral text-white flex items-center justify-center shrink-0">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div className="flex flex-col gap-1">
            <div className="font-black text-base text-ink">
              SERVER-SIDE REVISOR LOCKOUT ACTIVE (HTTP 403)
            </div>
            <p className="text-xs text-ink font-medium leading-relaxed">
              {lockoutError ||
                "Revisor verification audits are disabled while an active scored assessment is in progress."}
            </p>
          </div>
        </div>
      )}

      {/* Audit Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input Claim Form */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="tactile-card p-5 flex flex-col gap-4">
            <div className="font-black text-sm text-ink flex items-center gap-2">
              <SearchCheck className="w-4 h-4 text-brand-coral" />
              <span>Audit Target Claim</span>
            </div>

            {/* Sample Presets */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-ink-muted">Preset Test Scenarios:</label>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => setSampleClaim("valid")}
                  className="p-2 border border-ink/20 rounded bg-surface hover:bg-surface-warm font-bold text-[10px] text-center"
                >
                  Valid Claim
                </button>
                <button
                  type="button"
                  onClick={() => setSampleClaim("contradiction")}
                  className="p-2 border border-brand-coral/40 rounded bg-brand-coral/10 hover:bg-brand-coral/20 font-bold text-[10px] text-brand-coral text-center"
                >
                  Contradiction
                </button>
                <button
                  type="button"
                  onClick={() => setSampleClaim("ungrounded")}
                  className="p-2 border border-ink/20 rounded bg-surface hover:bg-surface-warm font-bold text-[10px] text-center"
                >
                  Ungrounded
                </button>
              </div>
            </div>

            {/* Candidate Text Input */}
            <div className="flex flex-col gap-2 pt-2 border-t border-ink/10">
              <label className="text-xs font-bold text-ink">Candidate Text to Audit:</label>
              <textarea
                rows={4}
                value={candidateText}
                onChange={(e) => setCandidateText(e.target.value)}
                placeholder="Paste explanation, student answer, or hypothesis to review..."
                className="tactile-input text-xs"
              />
            </div>

            {/* Query or Topic Scope Input */}
            <div className="flex flex-col gap-2 pt-2 border-t border-ink/10">
              <label className="text-xs font-bold text-ink flex items-center justify-between">
                <span>Retrieval Topic / Subject Query:</span>
                <span className="text-[10px] text-ink-muted">Min 2 characters</span>
              </label>
              <input
                type="text"
                value={queryTopic}
                onChange={(e) => setQueryTopic(e.target.value)}
                placeholder="e.g. Armstrong axioms, closure, normalization..."
                className="tactile-input text-xs"
              />
              {queryTopic.trim().length > 0 && queryTopic.trim().length < 2 && (
                <span className="text-[10px] text-brand-coral font-bold">
                  Query or topic must be at least 2 characters.
                </span>
              )}
            </div>

            {/* Deterministic Check Toggle */}
            <div className="flex items-center gap-2 pt-2 border-t border-ink/10">
              <input
                type="checkbox"
                id="detCheck"
                checked={checkDeterministicLogic}
                onChange={(e) => setCheckDeterministicLogic(e.target.checked)}
                className="w-4 h-4 accent-brand-yellow cursor-pointer"
              />
              <label htmlFor="detCheck" className="text-xs font-bold text-ink cursor-pointer">
                Enforce Deterministic Relational Closure Check (ADR 0002)
              </label>
            </div>

            <button
              onClick={handleRunAudit}
              disabled={isAuditing || !candidateText.trim() || queryTopic.trim().length < 2}
              className="tactile-btn-coral text-xs py-2.5 font-black text-white"
            >
              <FileCheck2 className={`w-3.5 h-3.5 ${isAuditing ? "animate-spin" : ""}`} />
              <span>{isAuditing ? "Cross-Examining Evidence..." : "Run Revisor Audit"}</span>
            </button>
          </div>
        </div>

        {/* Right: Revisor Audit Report */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-ink flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-brand-coral" />
              <span>Verification Audit Report</span>
            </h3>
            {(reviewResult?.model_used || reviewResult?.model_name) && (
              <span className="tactile-tag bg-surface text-ink text-[10px]">
                Model: {reviewResult.model_used || reviewResult.model_name}
              </span>
            )}
          </div>

          {reviewResult ? (() => {
            const auditStatus = reviewResult.audit_status || reviewResult.status || "insufficient_evidence";
            const summaryText = reviewResult.summary || reviewResult.audit_report || "";
            const verifiedPoints = reviewResult.verified_points || reviewResult.supported_claims || [];
            const flaggedIssues = reviewResult.flagged_issues || reviewResult.unsupported_claims || [];
            const citationsVerified = reviewResult.citations_verified || reviewResult.citations || [];
            const isContradiction =
              auditStatus === "contradiction_detected" ||
              auditStatus === "DETERMINISTIC_CONTRADICTION" ||
              Boolean(reviewResult.deterministic_validation?.contradiction_detected);
            const isVerified =
              auditStatus === "verified_grounded" || auditStatus === "VERIFIED_GROUNDED";

            return (
              <div className="tactile-card p-6 flex flex-col gap-4">
                {/* Verdict Banner */}
                <div
                  className={`p-4 border-2 border-ink rounded-friendly-sm flex items-center justify-between ${
                    isVerified
                      ? "bg-brand-green/20"
                      : isContradiction
                      ? "bg-brand-coral/25 border-brand-coral"
                      : "bg-brand-yellow/30"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {isVerified ? (
                      <CheckCircle2 className="w-7 h-7 text-brand-green" />
                    ) : isContradiction ? (
                      <XCircle className="w-7 h-7 text-brand-coral" />
                    ) : (
                      <AlertTriangle className="w-7 h-7 text-brand-yellow" />
                    )}
                    <div>
                      <div className="font-black text-base text-ink uppercase">{auditStatus.replace(/_/g, " ")}</div>
                      <div className="text-xs text-ink font-bold">
                        {isContradiction
                          ? "Deterministic mathematical contradiction overrides generative consensus!"
                          : isVerified
                          ? "Audit evaluated and verified against authoritative course materials"
                          : "Audit flagged issues or insufficient grounding in course evidence"}
                      </div>
                    </div>
                  </div>
                  {isContradiction && (
                    <span className="tactile-tag bg-brand-coral text-white text-[10px] uppercase">
                      CONTRADICTION DETECTED
                    </span>
                  )}
                </div>

                {/* Audit Report Prose Summary */}
                {summaryText && (
                  <div className="p-4 bg-surface-warm/30 border border-ink/20 rounded-friendly-sm text-xs text-ink leading-relaxed font-medium">
                    {summaryText}
                  </div>
                )}

                {/* Verified Points */}
                {verifiedPoints.length > 0 && (
                  <div className="flex flex-col gap-1.5 pt-2 border-t border-ink/10">
                    <div className="text-xs font-bold text-brand-green flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Verified Points:</span>
                    </div>
                    <ul className="list-disc list-inside text-xs text-ink font-medium space-y-1">
                      {verifiedPoints.map((claim, idx) => (
                        <li key={idx}>{claim}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Flagged Issues */}
                {flaggedIssues.length > 0 && (
                  <div className="flex flex-col gap-1.5 pt-2 border-t border-ink/10">
                    <div className="text-xs font-bold text-brand-coral flex items-center gap-1.5">
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Flagged Issues / Contradictions:</span>
                    </div>
                    <ul className="list-disc list-inside text-xs text-ink font-medium space-y-1">
                      {flaggedIssues.map((issue, idx) => (
                        <li key={idx}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Suggested Revision if provided */}
                {reviewResult.suggested_revision && (
                  <div className="p-3 bg-brand-cyan/10 border border-brand-cyan/40 rounded-friendly-sm text-xs text-ink">
                    <div className="font-bold text-brand-cyan mb-1">Suggested Revision:</div>
                    <p className="font-medium">{reviewResult.suggested_revision}</p>
                  </div>
                )}

                {/* Citations */}
                <div className="flex flex-col gap-2 pt-3 border-t border-ink/10">
                  <div className="text-xs font-bold text-ink-muted">Verified Evidence Sources:</div>
                  {citationsVerified.length === 0 ? (
                    <span className="text-xs text-ink-faint italic">No course citations available.</span>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {citationsVerified.map((c, i) => (
                        <span key={i} className="tactile-tag bg-brand-cyan/20 text-ink text-xs font-mono">
                          <BookOpen className="w-3 h-3 text-brand-cyan" />
                          <span>{c}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })() : (
            <div className="tactile-card p-12 text-center text-ink-muted flex flex-col items-center justify-center gap-2 min-h-[280px]">
              <SearchCheck className="w-8 h-8 text-ink-faint" />
              <div className="font-bold text-sm">No Audit Conducted Yet</div>
              <p className="text-xs max-w-sm font-medium">
                Enter a claim and retrieval topic on the left and trigger an adversarial audit to cross-examine evidence
                against official syllabus materials.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
