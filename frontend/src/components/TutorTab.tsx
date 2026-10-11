"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Lock,
  MessageSquare,
  Send,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { CourseResponse, TutorQueryResponse, UserResponse } from "../types";
import { ApiError, recallApi } from "../lib/api-client";
import { StructuredExplanation } from "./StructuredExplanation";

interface TutorTabProps {
  course: CourseResponse | null;
  currentUser: UserResponse | null;
  hasActiveScoredAssessment: boolean;
}

export function TutorTab({
  course,
  currentUser,
  hasActiveScoredAssessment,
}: TutorTabProps) {
  const isOS =
    course?.code.toUpperCase() === "CS301" ||
    course?.title.toLowerCase().includes("operating system");
  const isNetworks =
    course?.code.toUpperCase() === "CS305" ||
    course?.title.toLowerCase().includes("network");
  const isDBMS = !isOS && !isNetworks;

  const sample1 = isOS
    ? "Can you explain deadlock conditions and prevention strategies?"
    : isNetworks
    ? "Can you explain the TCP 3-way handshake and reliability?"
    : "Can you explain Armstrong's Axioms and transitivity?";

  const sample2 = isOS
    ? "What is virtual memory and how does page replacement work?"
    : isNetworks
    ? "What is the difference between TCP and UDP flow control?"
    : "What is minimal cover and why is it useful?";

  const [query, setQuery] = useState<string>(sample1);
  const [isAsking, setIsAsking] = useState<boolean>(false);
  const [response, setResponse] = useState<TutorQueryResponse | null>(null);
  const [lockoutError, setLockoutError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  useEffect(() => {
    setQuery(sample1);
    setResponse(null);
    setGeneralError(null);
    setLockoutError(null);
  }, [course?.id, sample1]);

  const handleAskTutor = async () => {
    if (!course || !currentUser || !query.trim()) return;

    // Client-side awareness of active assessment lockout
    if (hasActiveScoredAssessment) {
      setLockoutError(
        "AI Tutor assistance is strictly locked out during active scored assessments (ADR 0002). " +
        "Complete or submit your scored assessment before requesting conceptual guidance."
      );
      setResponse(null);
      return;
    }

    setIsAsking(true);
    setLockoutError(null);
    setGeneralError(null);
    setResponse(null);

    try {
      const resp = await recallApi.askTutor(course.id, currentUser.id, query);
      setResponse(resp);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.problem.code === "ASSESSMENT_LOCKOUT") {
        setLockoutError(err.problem.detail);
      } else if (
        err instanceof ApiError &&
        err.problem.code === "FORBIDDEN" &&
        err.problem.detail.toLowerCase().includes("not enrolled")
      ) {
        // Automatically enroll student in this course and retry query once
        try {
          await recallApi.enrollUser(currentUser.id, course.id);
          const retryResp = await recallApi.askTutor(course.id, currentUser.id, query);
          setResponse(retryResp);
          return;
        } catch (retryErr: unknown) {
          if (retryErr instanceof ApiError) {
            setGeneralError(retryErr.problem.detail || retryErr.problem.title);
          } else {
            setGeneralError(retryErr instanceof Error ? retryErr.message : "Failed to query Grounded Tutor.");
          }
        }
      } else if (err instanceof ApiError) {
        setGeneralError(err.problem.detail || err.problem.title);
      } else {
        setGeneralError(err instanceof Error ? err.message : "Failed to query Grounded Tutor.");
      }
    } finally {
      setIsAsking(false);
    }
  };

  if (!course) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <BookOpen className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">Select a course to interact with the Grounded AI Tutor.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Tutor Header */}
      <section className="tactile-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-yellow text-ink">SLM ROLE A</span>
            <span className="text-xs font-bold text-ink-muted">Grounded Explainer</span>
          </div>
          <h2 className="text-2xl font-black text-ink">Grounded AI Tutor</h2>
          <p className="text-sm text-ink-muted mt-1 max-w-2xl font-medium">
            Provides pedagogical concept explanations strictly bounded to verified lecture materials.
            Holds zero grading authority and abstains rather than synthesizing hallucinations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="tactile-tag bg-brand-green text-ink text-xs">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Syllabus Bound</span>
          </span>
          <span className="tactile-tag bg-brand-coral text-white text-xs">
            <Lock className="w-3.5 h-3.5" />
            <span>403 Lockout Enforced</span>
          </span>
        </div>
      </section>

      {/* Active Assessment Lockout Alert (if active) */}
      {(hasActiveScoredAssessment || lockoutError) && (
        <div className="tactile-card border-brand-coral bg-brand-coral/15 p-6 flex items-start gap-4 animate-shake">
          <div className="w-10 h-10 rounded-friendly-sm bg-brand-coral text-white flex items-center justify-center shrink-0">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div className="flex flex-col gap-1">
            <div className="font-black text-base text-ink">
              SERVER-SIDE ASSESSMENT LOCKOUT ACTIVE (HTTP 403)
            </div>
            <p className="text-xs text-ink font-medium leading-relaxed">
              {lockoutError ||
                "Free-form AI tutor queries are strictly rejected while a scored assessment is in progress. " +
                "Recall enforces server-side access control so generative models cannot be consulted for exam assistance."}
            </p>
          </div>
        </div>
      )}

      {/* General / Verification Error Alert */}
      {generalError && (
        <div className="tactile-card border-brand-coral bg-brand-coral/15 p-5 flex items-start gap-4 animate-shake">
          <div className="w-9 h-9 rounded-friendly-sm bg-brand-coral text-white flex items-center justify-center shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex flex-col gap-1">
            <div className="font-black text-sm text-ink">
              Grounded AI Tutor Notice
            </div>
            <p className="text-xs text-ink font-medium leading-relaxed">
              {generalError}
            </p>
          </div>
        </div>
      )}

      {/* Inquire Sandbox */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Query Formulation */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="tactile-card p-5 flex flex-col gap-4">
            <div className="font-black text-sm text-ink flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brand-yellow" />
              <span>Ask Syllabus Question</span>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-ink-muted">Sample Questions:</label>
              <div className="flex flex-col gap-1.5 text-xs">
                <button
                  type="button"
                  onClick={() => setQuery(sample1)}
                  className="p-2 border border-ink/20 rounded bg-surface hover:bg-surface-warm text-left text-[11px] font-medium"
                >
                  &quot;{sample1}&quot;
                </button>
                <button
                  type="button"
                  onClick={() => setQuery(sample2)}
                  className="p-2 border border-ink/20 rounded bg-surface hover:bg-surface-warm text-left text-[11px] font-medium"
                >
                  &quot;{sample2}&quot;
                </button>
                {isDBMS && (
                  <button
                    type="button"
                    onClick={() =>
                      setQuery(
                        "Consider a relation EMPLOYEE_DEPT (Emp_ID, Emp_Name, Dept_ID, Dept_Name) with PK Emp_ID and FDs: Emp_ID -> Emp_Name, Emp_ID -> Dept_ID, Dept_ID -> Dept_Name. Check if the above is in 3NF; if not, convert it into 3NF."
                      )
                    }
                    className="p-2 border border-brand-yellow/50 rounded bg-brand-yellow/15 hover:bg-brand-yellow/25 text-left text-[11px] font-bold text-ink"
                  >
                    &quot;Check 3NF and decompose EMPLOYEE_DEPT&quot; (3NF Decomposition)
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setQuery("What are quantum algorithms for sorting data?")}
                  className="p-2 border border-brand-coral/40 rounded bg-brand-coral/10 hover:bg-brand-coral/20 text-left text-[11px] font-bold text-brand-coral"
                >
                  &quot;What are quantum algorithms?&quot; (Out-of-syllabus test)
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-ink/10">
              <label className="text-xs font-bold text-ink">Your Question:</label>
              <textarea
                rows={4}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask an academic question regarding course materials..."
                className="tactile-input text-xs"
              />
            </div>

            <button
              onClick={handleAskTutor}
              disabled={isAsking || !query.trim()}
              className="tactile-btn-yellow text-xs py-2.5 font-black"
            >
              <Send className={`w-3.5 h-3.5 ${isAsking ? "animate-spin" : ""}`} />
              <span>{isAsking ? "Retrieving & Generating Answer..." : "Ask Recall Tutor"}</span>
            </button>
          </div>
        </div>

        {/* Right: Grounded Response & Verified Citations */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-ink flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-brand-yellow" />
              <span>Grounded Explanation</span>
            </h3>
            {(response?.model_used || response?.model_name) && (
              <span className="tactile-tag bg-surface text-ink text-[10px]">
                Model: {response.model_used || response.model_name}
              </span>
            )}
          </div>

          {response ? (
            <div className="tactile-card p-6 flex flex-col gap-4">
              {/* Abstention Banner if out-of-syllabus */}
              {response.abstention_recommended ? (
                <div className="p-4 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-brand-coral shrink-0 mt-0.5" />
                  <div>
                    <div className="font-black text-xs text-brand-coral">
                      HONEST ABSTENTION APPLIED (UNVERIFIED EVIDENCE)
                    </div>
                    <p className="text-xs text-ink font-medium mt-1">
                      The Grounded Tutor abstained from answering this question because official course
                      materials do not contain verified evidence for this concept.
                    </p>
                  </div>
                </div>
              ) : null}

              {/* Structured Pedagogical Explanation */}
              <StructuredExplanation content={response.answer} />

              {/* Verified Sources List */}
              <div className="flex flex-col gap-2 pt-3 border-t border-ink/10">
                <div className="text-xs font-bold text-ink-muted">Course Sources:</div>
                {(!response.citations || response.citations.length === 0) ? (
                  <span className="text-xs text-ink-faint italic">No sources cited.</span>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {response.citations.map((c, i) => (
                      <span
                        key={i}
                        className="tactile-tag bg-brand-cyan/20 text-ink text-xs font-mono"
                        title="Authoritative curriculum citation"
                      >
                        <BookOpen className="w-3 h-3 text-brand-cyan" />
                        <span>{c}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Performance & Token Metadata */}
              <div className="pt-2 border-t border-ink/10 flex items-center justify-between text-[11px] text-ink-muted font-mono">
                <span>Retrieved Chunks: {response.retrieved_chunks_count}</span>
                {response.latency_ms && <span>Latency: {response.latency_ms}ms</span>}
                {response.prompt_tokens && response.completion_tokens && (
                  <span>
                    Tokens: {response.prompt_tokens} in / {response.completion_tokens} out
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div className="tactile-card p-12 text-center text-ink-muted flex flex-col items-center justify-center gap-2 min-h-[280px]">
              <MessageSquare className="w-8 h-8 text-ink-faint" />
              <div className="font-bold text-sm">Awaiting Student Question</div>
              <p className="text-xs max-w-sm font-medium">
                Ask an academic question on the left to receive grounded explanations and course sources.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
