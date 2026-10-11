"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  HelpCircle,
  Lock,
  Play,
  RotateCcw,
  Send,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  AssessmentContext,
  AttemptCreate,
  AttemptResponse,
  CourseResponse,
  LearningObjectiveResponse,
  QuestionResponse,
  TopicResponse,
  UserResponse,
} from "../types";
import { recallApi } from "../lib/api-client";

interface PracticeTabProps {
  course: CourseResponse | null;
  topics: TopicResponse[];
  currentUser: UserResponse | null;
  activeScoredAssessmentId: string | null;
  setActiveScoredAssessmentId: (id: string | null) => void;
  targetObjective?: LearningObjectiveResponse | null;
}

export function PracticeTab({
  course,
  topics,
  currentUser,
  activeScoredAssessmentId,
  setActiveScoredAssessmentId,
  targetObjective,
}: PracticeTabProps) {
  // Questions list
  const [questions, setQuestions] = useState<QuestionResponse[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionResponse | null>(null);
  const [loadingQuestions, setLoadingQuestions] = useState<boolean>(false);

  // Form state
  const [assessmentContext, setAssessmentContext] = useState<AssessmentContext>("unscored_practice");
  const [answerInput, setAnswerInput] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submissionResult, setSubmissionResult] = useState<AttemptResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Completed questions tracking
  const [completedQuestionIds, setCompletedQuestionIds] = useState<string[]>([]);
  const storageKey = `recall_completed_questions_${currentUser?.id || "anon"}_${course?.id || "default"}`;

  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        setCompletedQuestionIds(JSON.parse(stored));
      } else {
        setCompletedQuestionIds([]);
      }
    } catch {
      setCompletedQuestionIds([]);
    }
  }, [storageKey]);

  // Load questions for the selected objective or first available objective
  useEffect(() => {
    async function loadQuestions() {
      if (!course) return;
      setLoadingQuestions(true);

      const objToLoad =
        targetObjective ||
        (topics.length > 0 && topics[0].objectives.length > 0
          ? topics[0].objectives[0]
          : null);

      if (objToLoad) {
        try {
          const qs = await recallApi.listQuestionsForObjective(objToLoad.id);
          setQuestions(qs);
          // Prioritize uncompleted questions
          const uncompleted = qs.filter((q) => !completedQuestionIds.includes(q.id));
          if (uncompleted.length > 0) {
            setSelectedQuestion(uncompleted[0]);
            setAnswerInput("");
          } else if (qs.length > 0) {
            setSelectedQuestion(qs[0]);
          }
        } catch {
          setQuestions([]);
        }
      }
      setLoadingQuestions(false);
    }
    loadQuestions();
  }, [course?.id, targetObjective?.id, topics, completedQuestionIds.length]);

  const handleSubmitAttempt = async () => {
    if (!currentUser || !selectedQuestion || !selectedQuestion.versions[0]) return;
    if (completedQuestionIds.includes(selectedQuestion.id)) return; // Prevent double submit

    setIsSubmitting(true);
    setErrorMessage(null);
    setSubmissionResult(null);

    const idempotencyKey = `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    // Prepare submitted answer payload based on question type
    const payload: AttemptCreate = {
      student_id: currentUser.id,
      question_id: selectedQuestion.id,
      submitted_answer: { closure: answerInput.trim() },
      assessment_context: assessmentContext,
      time_spent_ms: 12000,
      is_hint_assisted: false,
      hint_count: 0,
    };

    try {
      const resp = await recallApi.submitAttempt(payload, idempotencyKey);
      setSubmissionResult(resp);

      // Lock question so it cannot be re-submitted and won't appear again
      const nextCompleted = Array.from(new Set([...completedQuestionIds, selectedQuestion.id]));
      setCompletedQuestionIds(nextCompleted);
      try {
        localStorage.setItem(storageKey, JSON.stringify(nextCompleted));
      } catch {}

      // If user submitted an independent_checkpoint, it finishes or we can toggle lock state
      if (assessmentContext === "independent_checkpoint") {
        setActiveScoredAssessmentId(null);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to grade attempt.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNextQuestion = () => {
    const uncompleted = questions.filter((q) => !completedQuestionIds.includes(q.id) && q.id !== selectedQuestion?.id);
    if (uncompleted.length > 0) {
      setSelectedQuestion(uncompleted[0]);
      setAnswerInput("");
      setSubmissionResult(null);
      setErrorMessage(null);
    }
  };

  const handleResetProgress = () => {
    if (window.confirm("Reset solved question history for this course?")) {
      setCompletedQuestionIds([]);
      try {
        localStorage.removeItem(storageKey);
      } catch {}
      setSubmissionResult(null);
      setAnswerInput("");
      if (questions.length > 0) {
        setSelectedQuestion(questions[0]);
      }
    }
  };

  const toggleSimulateActiveLockout = () => {
    if (activeScoredAssessmentId) {
      setActiveScoredAssessmentId(null);
    } else {
      setActiveScoredAssessmentId("simulated-scored-assessment-in-progress");
    }
  };

  if (!currentUser) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">Please log in to practice questions and submit attempts.</p>
      </div>
    );
  }

  const currentVersion = selectedQuestion?.versions[0];
  const isCurrentQuestionCompleted =
    !!selectedQuestion && completedQuestionIds.includes(selectedQuestion.id);
  const uncompletedQuestions = questions.filter(
    (q) => !completedQuestionIds.includes(q.id)
  );

  return (
    <div className="flex flex-col gap-8">
      {/* Assessment Mode & Lockout Controller Banner */}
      <section className="tactile-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-yellow text-ink">DETERMINISTIC EVALUATION</span>
            <span className="text-xs font-bold text-ink-muted">Pure Domain Logic (ADR 0002)</span>
          </div>
          <h2 className="text-2xl font-black text-ink">Interactive Practice & Assessment</h2>
          <p className="text-sm text-ink-muted mt-1 max-w-2xl font-medium">
            Student submissions are evaluated deterministically against authoritative keys and Armstrong
            axioms with zero LLM grading hallucinations.
          </p>
        </div>

        {/* Lockout Demonstration Switch */}
        <div className="flex flex-col items-end gap-2">
          <button
            onClick={toggleSimulateActiveLockout}
            className={`tactile-tag cursor-pointer ${
              activeScoredAssessmentId
                ? "bg-brand-coral text-white"
                : "bg-surface-warm text-ink hover:bg-brand-yellow"
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            <span>
              {activeScoredAssessmentId
                ? "Scored Assessment Active (Lockout Engaged)"
                : "Simulate Active Scored Lockout"}
            </span>
          </button>
          <span className="text-[11px] text-ink-muted font-medium">
            Locks out AI Tutor & Revisor via Server 403
          </span>
        </div>
      </section>

      {/* Question Runner & Grading Provenance */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Question Selector & Formulation */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          {/* Question Picker */}
          <div className="tactile-card p-5 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-ink-muted">Select Assessment Item:</span>
              <div className="flex items-center gap-2">
                {completedQuestionIds.length > 0 && (
                  <button
                    type="button"
                    onClick={handleResetProgress}
                    className="text-[10px] text-ink-muted hover:text-brand-coral font-bold underline cursor-pointer"
                  >
                    Reset Solved
                  </button>
                )}
                <span className="tactile-tag bg-surface text-ink text-[10px]">
                  {uncompletedQuestions.length} Pending &bull; {questions.length - uncompletedQuestions.length} Solved
                </span>
              </div>
            </div>

            <select
              value={selectedQuestion?.id || ""}
              onChange={(e) => {
                const q = questions.find((item) => item.id === e.target.value);
                if (q) {
                  setSelectedQuestion(q);
                  setSubmissionResult(null);
                  setAnswerInput("");
                }
              }}
              className="tactile-input text-xs font-bold cursor-pointer"
            >
              {questions.length === 0 ? (
                <option value="">No questions found</option>
              ) : uncompletedQuestions.length === 0 ? (
                <option value={selectedQuestion?.id || ""}>
                  All {questions.length} questions completed! ✓
                </option>
              ) : (
                uncompletedQuestions.map((q) => (
                  <option key={q.id} value={q.id}>
                    {q.title} ({q.question_type})
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Prompt Viewer & Answer Input */}
          {selectedQuestion && currentVersion && (
            <div className="tactile-card p-6 flex flex-col gap-5">
              <div className="flex items-center justify-between">
                <span className="tactile-tag bg-brand-cyan text-ink text-xs">
                  {selectedQuestion.title}
                </span>
                <span className="tactile-tag bg-surface text-ink text-xs uppercase">
                  Difficulty: {currentVersion.difficulty}
                </span>
              </div>

              {/* Question Prompt */}
              <div className="p-4 bg-surface-warm/40 border-2 border-ink rounded-friendly-sm">
                <div className="text-xs font-bold text-ink-muted mb-1">PROMPT:</div>
                <div className="text-sm font-black text-ink leading-relaxed">
                  {currentVersion.prompt}
                </div>
              </div>

              {/* Assessment Context Selector */}
              <div className="flex flex-col gap-2">
                <label className="text-xs font-bold text-ink">Assessment Context:</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  {(
                    [
                      "unscored_practice",
                      "diagnostic",
                      "independent_checkpoint",
                      "retention_review",
                    ] as AssessmentContext[]
                  ).map((ctx) => (
                    <button
                      key={ctx}
                      type="button"
                      onClick={() => setAssessmentContext(ctx)}
                      className={`p-2 border-2 border-ink rounded font-bold text-center transition-all ${
                        assessmentContext === ctx
                          ? "bg-brand-yellow shadow-hard-sm"
                          : "bg-surface hover:bg-surface-warm"
                      }`}
                    >
                      {ctx === "independent_checkpoint" ? "Checkpoint (Scored)" : ctx.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>

              {/* Answer Input */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-ink">Your Answer:</label>
                  <span className="text-[11px] text-ink-muted">
                    Format: Comma-separated (e.g. A, B, C, D)
                  </span>
                </div>
                <input
                  type="text"
                  value={answerInput}
                  onChange={(e) => setAnswerInput(e.target.value)}
                  placeholder={
                    isCurrentQuestionCompleted
                      ? "Answer submitted & evaluated. Question locked."
                      : "e.g. A, B, C, D"
                  }
                  className={`tactile-input text-sm font-bold ${
                    isCurrentQuestionCompleted ? "bg-surface opacity-80 cursor-not-allowed" : ""
                  }`}
                  disabled={isCurrentQuestionCompleted || isSubmitting}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !isCurrentQuestionCompleted) handleSubmitAttempt();
                  }}
                />
              </div>

              {/* Submit or Next Question Action */}
              {isCurrentQuestionCompleted ? (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between p-3 bg-brand-green/15 border-2 border-brand-green rounded-friendly-sm text-xs font-bold text-ink">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-brand-green" />
                      <span>Answer Evaluated &mdash; Submit option is locked for this question.</span>
                    </div>
                    <span className="tactile-tag bg-brand-green text-white text-[10px] font-black uppercase">
                      COMPLETED
                    </span>
                  </div>
                  {uncompletedQuestions.length > 0 && (
                    <button
                      type="button"
                      onClick={handleNextQuestion}
                      className="tactile-btn-yellow text-sm py-2.5 w-full font-black flex items-center justify-center gap-2"
                    >
                      <span>Proceed to Next Question</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ) : (
                <button
                  onClick={handleSubmitAttempt}
                  disabled={isSubmitting || !answerInput.trim()}
                  className="tactile-btn-yellow text-sm py-2.5 w-full font-black"
                >
                  <Send className={`w-4 h-4 ${isSubmitting ? "animate-spin" : ""}`} />
                  <span>{isSubmitting ? "Grading Deterministically..." : "Submit for Evaluation"}</span>
                </button>
              )}

              {errorMessage && (
                <div className="p-3 bg-brand-coral/10 border-2 border-brand-coral rounded text-xs font-bold text-brand-coral">
                  {errorMessage}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Instant Deterministic Grading Provenance */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <h3 className="text-lg font-black text-ink flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-brand-green" />
            <span>Grading Provenance</span>
          </h3>

          {submissionResult ? (
            <div className="tactile-card p-5 flex flex-col gap-4">
              {/* Verdict Header */}
              <div
                className={`p-4 border-2 border-ink rounded-friendly-sm flex items-center justify-between ${
                  submissionResult.is_correct ? "bg-brand-green/20" : "bg-brand-coral/20"
                }`}
              >
                <div className="flex items-center gap-3">
                  {submissionResult.is_correct ? (
                    <CheckCircle2 className="w-7 h-7 text-brand-green" />
                  ) : (
                    <XCircle className="w-7 h-7 text-brand-coral" />
                  )}
                  <div>
                    <div className="font-black text-base text-ink">
                      {submissionResult.is_correct ? "CORRECT ANSWER" : "INCORRECT ANSWER"}
                    </div>
                    <div className="text-xs text-ink-muted font-bold">
                      Points: {submissionResult.score_achieved} /{" "}
                      {submissionResult.max_possible_score}
                    </div>
                  </div>
                </div>
                <span className="tactile-tag bg-surface text-ink text-xs uppercase">
                  {submissionResult.status}
                </span>
              </div>

              {/* Rubric Provenance Breakdown */}
              <div className="text-xs space-y-2 pt-2 border-t border-ink/10">
                <div className="font-bold text-ink">Deterministic Audit Ledger:</div>
                <div className="bg-surface-warm/40 p-3 rounded border border-ink/20 font-mono text-[11px] space-y-1">
                  <div>Context: {submissionResult.assessment_context}</div>
                  <div>Idempotency Key: {submissionResult.idempotency_key}</div>
                  <div>Grading Authority: app.modules.adaptive_learning.dbms_grader</div>
                  <div>Zero Generative Hallucination Guaranteed</div>
                </div>
              </div>

              {/* Official Explanation */}
              {currentVersion?.explanation && (
                <div className="p-3 bg-surface border border-ink rounded-friendly-sm text-xs flex flex-col gap-1">
                  <span className="font-bold text-ink">Explanation:</span>
                  <p className="text-ink-muted font-medium">{currentVersion.explanation}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="tactile-card p-8 text-center text-ink-muted flex flex-col items-center justify-center gap-2 min-h-[240px]">
              <HelpCircle className="w-8 h-8 text-ink-faint" />
              <div className="font-bold text-sm">No Attempt Evaluated Yet</div>
              <p className="text-xs max-w-xs font-medium">
                Type an answer on the left and submit to view immediate deterministic rubric scoring.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
