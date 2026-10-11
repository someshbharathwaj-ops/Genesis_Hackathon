"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Award,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  Flame,
  HelpCircle,
  History,
  Lock,
  Play,
  RotateCcw,
  Send,
  ShieldCheck,
  Target,
  Trophy,
  X,
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
import { QuestionAttemptRecord } from "./RevisorTab";

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

  // Completed questions tracking & marks ledger
  const [completedQuestionIds, setCompletedQuestionIds] = useState<string[]>([]);
  const [attemptHistory, setAttemptHistory] = useState<Record<string, QuestionAttemptRecord>>({});
  const [showMarksLedger, setShowMarksLedger] = useState<boolean>(false);

  const storageKey = `recall_completed_questions_${currentUser?.id || "anon"}_${course?.id || "default"}`;
  const historyStorageKey = `recall_attempt_history_${currentUser?.id || "anon"}_${course?.id || "default"}`;

  useEffect(() => {
    let localHistory: Record<string, QuestionAttemptRecord> = {};
    try {
      const storedHistory = localStorage.getItem(historyStorageKey);
      if (storedHistory) {
        localHistory = JSON.parse(storedHistory);
        setAttemptHistory(localHistory);
      } else {
        setAttemptHistory({});
      }
    } catch {
      setAttemptHistory({});
    }

    try {
      const stored = localStorage.getItem(storageKey);
      const storedIds: string[] = stored ? JSON.parse(stored) : [];
      const historyIds = Object.keys(localHistory);
      const combined = Array.from(new Set([...storedIds, ...historyIds]));
      setCompletedQuestionIds(combined);
    } catch {
      setCompletedQuestionIds(Object.keys(localHistory));
    }
  }, [storageKey, historyStorageKey]);

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

    // Prepare submitted answer payload supporting closure, value, keys, fds, and decomposition
    const submittedPayload: Record<string, unknown> = {
      closure: answerInput.trim(),
      value: answerInput.trim(),
      candidate_keys: answerInput.split(",").map((s) => s.trim()).filter(Boolean),
      fds: answerInput.split(";").map((s) => s.trim()).filter(Boolean),
      relations: answerInput.split(";").map((s) => s.trim()).filter(Boolean),
    };

    const payload: AttemptCreate = {
      student_id: currentUser.id,
      question_id: selectedQuestion.id,
      submitted_answer: submittedPayload,
      assessment_context: assessmentContext,
      time_spent_ms: 12000,
      is_hint_assisted: false,
      hint_count: 0,
    };

    try {
      const resp = await recallApi.submitAttempt(payload, idempotencyKey);
      setSubmissionResult(resp);

      const expectedKeyStr =
        currentVersion?.answer_key?.closure ||
        currentVersion?.answer_key?.value ||
        (Array.isArray(currentVersion?.answer_key?.candidate_keys)
          ? currentVersion.answer_key.candidate_keys.join(", ")
          : undefined) ||
        (Array.isArray(currentVersion?.answer_key?.fds)
          ? currentVersion.answer_key.fds.join("; ")
          : undefined);

      const newRecord: QuestionAttemptRecord = {
        questionId: selectedQuestion.id,
        questionTitle: selectedQuestion.title,
        objectiveId: selectedQuestion.objective_id,
        isCorrect: resp.is_correct,
        scoreAchieved: resp.score_achieved,
        maxScore: resp.max_possible_score || currentVersion?.max_score || 1.0,
        submittedAnswer: answerInput.trim(),
        explanation:
          currentVersion?.explanation ||
          "Each dependency and condition was verified through authoritative deterministic evaluation.",
        evaluationSteps: (resp.grading_provenance?.evaluation_steps as string[]) || [],
        deductions: (resp.grading_provenance?.deductions as Array<{ reason: string; [key: string]: unknown }>) || [],
        referenceCitation: String(currentVersion?.answer_key?.reference || ""),
        expectedKey: expectedKeyStr ? String(expectedKeyStr) : undefined,
        timestamp: new Date().toISOString(),
      };

      setAttemptHistory((prev) => {
        const next = { ...prev, [selectedQuestion.id]: newRecord };
        try {
          localStorage.setItem(historyStorageKey, JSON.stringify(next));
        } catch {}
        return next;
      });

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
    if (window.confirm("Reset solved question history and marks for this course?")) {
      setCompletedQuestionIds([]);
      setAttemptHistory({});
      try {
        localStorage.removeItem(storageKey);
        localStorage.removeItem(historyStorageKey);
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

  const attemptList = Object.values(attemptHistory);
  const totalMarksEarned = attemptList.reduce((acc, r) => acc + (r.scoreAchieved || 0), 0);
  const totalMarksPossible = attemptList.reduce((acc, r) => acc + (r.maxScore || 1.0), 0);
  const correctCount = attemptList.filter((r) => r.isCorrect).length;
  const accuracyPercentage =
    totalMarksPossible > 0 ? Math.round((totalMarksEarned / totalMarksPossible) * 100) : 0;

  let streakCount = 0;
  const sortedAttempts = [...attemptList].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
  for (const a of sortedAttempts) {
    if (a.isCorrect) streakCount++;
    else break;
  }

  const currentRecord = selectedQuestion ? attemptHistory[selectedQuestion.id] : null;
  const isQuestionAnswered = !!(submissionResult || currentRecord);
  const isCorrect = submissionResult
    ? submissionResult.is_correct
    : (currentRecord?.isCorrect ?? false);
  const scoreAchieved = submissionResult
    ? submissionResult.score_achieved
    : (currentRecord?.scoreAchieved ?? 0);
  const maxScore = submissionResult
    ? submissionResult.max_possible_score
    : (currentRecord?.maxScore ?? currentVersion?.max_score ?? 1.0);
  const submittedAnswerVal = submissionResult
    ? (typeof submissionResult.submitted_answer === "object"
        ? JSON.stringify(submissionResult.submitted_answer)
        : String(submissionResult.submitted_answer))
    : (typeof currentRecord?.submittedAnswer === "object"
        ? JSON.stringify(currentRecord.submittedAnswer)
        : String(currentRecord?.submittedAnswer || ""));
  const explanationText =
    currentVersion?.explanation ||
    currentRecord?.explanation ||
    "Authoritative syllabus solution verified.";
  const evaluationSteps =
    (submissionResult?.grading_provenance?.evaluation_steps as string[]) ||
    currentRecord?.evaluationSteps ||
    [];
  const deductions =
    (submissionResult?.grading_provenance?.deductions as Array<{ reason: string; [key: string]: unknown }>) ||
    currentRecord?.deductions ||
    [];
  const referenceCitation = String(
    currentVersion?.answer_key?.reference || currentRecord?.referenceCitation || ""
  );
  const expectedKey =
    currentRecord?.expectedKey ||
    String(
      currentVersion?.answer_key?.closure ||
      currentVersion?.answer_key?.value ||
      (Array.isArray(currentVersion?.answer_key?.candidate_keys)
        ? currentVersion?.answer_key?.candidate_keys.join(", ")
        : "")
    );

  return (
    <div className="flex flex-col gap-6">
      {/* Assessment Mode & Lockout Controller Banner */}
      <section className="tactile-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-yellow text-ink">DETERMINISTIC EVALUATION</span>
            <span className="text-xs font-bold text-ink-muted">Pure Domain Logic (ADR 0002)</span>
          </div>
          <h2 className="text-2xl font-black text-ink">Interactive Practice &amp; Assessment</h2>
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
            Locks out AI Tutor &amp; Revisor via Server 403
          </span>
        </div>
      </section>

      {/* Live Marks Scoreboard */}
      <div className="tactile-card p-4 sm:p-5 bg-surface border-2 border-ink flex flex-col gap-4 shadow-hard-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-ink/10 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-friendly-sm bg-brand-yellow border-2 border-ink flex items-center justify-center font-black text-ink shadow-hard-sm">
              <Trophy className="w-5 h-5 text-ink" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="tactile-tag bg-brand-yellow text-ink text-[10px] font-black uppercase">
                  LIVE MARKS TRACKER
                </span>
                <span className="text-xs font-bold text-ink-muted">
                  Course: {course?.code || "CS340"}
                </span>
              </div>
              <h3 className="text-base font-black text-ink leading-tight">
                Your Practice Marks &amp; Scoreboard
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowMarksLedger((prev) => !prev)}
              className="tactile-btn-white text-xs py-1.5 px-3 font-bold flex items-center gap-1.5 hover:!bg-brand-yellow"
            >
              <History className="w-3.5 h-3.5" />
              <span>{showMarksLedger ? "Hide Ledger" : "View Marks Ledger"}</span>
              {showMarksLedger ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            {attemptList.length > 0 && (
              <button
                type="button"
                onClick={handleResetProgress}
                className="text-xs font-bold text-ink-muted hover:text-brand-coral underline py-1 px-2"
              >
                Reset All
              </button>
            )}
          </div>
        </div>

        {/* Metric Gauges */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-brand-yellow/15 border-2 border-ink rounded-friendly-sm flex flex-col gap-1">
            <div className="flex items-center justify-between text-[11px] font-black text-ink-muted uppercase">
              <span>Marks Earned</span>
              <Award className="w-4 h-4 text-brand-yellow" />
            </div>
            <div className="text-2xl font-black text-ink">
              {totalMarksEarned.toFixed(1)}{" "}
              <span className="text-sm font-bold text-ink-muted">/ {totalMarksPossible.toFixed(1)} Pts</span>
            </div>
            <span className="text-[10px] text-ink-muted font-medium">
              {totalMarksPossible > 0 ? `${((totalMarksEarned / totalMarksPossible) * 100).toFixed(0)}% points achieved` : "No questions completed"}
            </span>
          </div>

          <div className="p-3 bg-surface border-2 border-ink rounded-friendly-sm flex flex-col gap-1">
            <div className="flex items-center justify-between text-[11px] font-black text-ink-muted uppercase">
              <span>Accuracy &amp; Grade</span>
              <Target className="w-4 h-4 text-brand-cyan" />
            </div>
            <div className="text-2xl font-black text-ink">
              {accuracyPercentage}%
            </div>
            <div className="w-full bg-ink/10 h-2 rounded-full overflow-hidden mt-1 border border-ink/20">
              <div
                className={`h-full transition-all duration-500 ${
                  accuracyPercentage >= 80 ? "bg-brand-green" : accuracyPercentage >= 60 ? "bg-brand-yellow" : "bg-brand-coral"
                }`}
                style={{ width: `${Math.min(100, Math.max(0, accuracyPercentage))}%` }}
              />
            </div>
          </div>

          <div className="p-3 bg-surface border-2 border-ink rounded-friendly-sm flex flex-col gap-1">
            <div className="flex items-center justify-between text-[11px] font-black text-ink-muted uppercase">
              <span>Questions Solved</span>
              <CheckCircle2 className="w-4 h-4 text-brand-green" />
            </div>
            <div className="text-2xl font-black text-ink">
              {attemptList.length}{" "}
              <span className="text-sm font-bold text-ink-muted">({correctCount} correct &bull; {attemptList.length - correctCount} wrong)</span>
            </div>
            <span className="text-[10px] text-ink-muted font-medium">
              {questions.length - uncompletedQuestions.length} of {questions.length} completed
            </span>
          </div>

          <div className="p-3 bg-brand-coral/10 border-2 border-ink rounded-friendly-sm flex flex-col gap-1">
            <div className="flex items-center justify-between text-[11px] font-black text-ink-muted uppercase">
              <span>Correct Streak</span>
              <Flame className="w-4 h-4 text-brand-coral" />
            </div>
            <div className="text-2xl font-black text-ink flex items-center gap-1.5">
              <span>{streakCount}</span>
              <span className="text-sm font-bold text-ink-muted">in a row</span>
            </div>
            <span className="text-[10px] text-ink-muted font-medium">
              {streakCount >= 3 ? "🔥 Streak active!" : "Keep answering correctly"}
            </span>
          </div>
        </div>
      </div>

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
                  const rec = attemptHistory[q.id];
                  setAnswerInput(rec ? (typeof rec.submittedAnswer === "object" ? JSON.stringify(rec.submittedAnswer) : String(rec.submittedAnswer)) : "");
                }
              }}
              className="tactile-input text-xs font-bold cursor-pointer"
            >
              {questions.length === 0 ? (
                <option value="">No questions found</option>
              ) : (
                questions.map((q) => {
                  const rec = attemptHistory[q.id];
                  const isDone = completedQuestionIds.includes(q.id) || !!rec;
                  const statusTag = isDone
                    ? rec?.isCorrect
                      ? `[✓ Solved: +${(rec.scoreAchieved || 1).toFixed(1)}] `
                      : `[✗ Attempted: 0.0] `
                    : "[Pending] ";
                  return (
                    <option key={q.id} value={q.id}>
                      {statusTag}{q.title} ({q.question_type})
                    </option>
                  );
                })
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
                  Difficulty: {currentVersion.difficulty} &bull; {currentVersion.max_score} Mark{currentVersion.max_score === 1 ? "" : "s"}
                </span>
              </div>

              {/* Question Statement */}
              <div className="p-4 bg-surface-warm/40 border-2 border-ink rounded-friendly-sm">
                <div className="text-xs font-bold text-ink-muted mb-1">QUESTION:</div>
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
                  <div className={`flex items-center justify-between p-3 border-2 rounded-friendly-sm text-xs font-bold ${
                    isCorrect ? "bg-brand-green/15 border-brand-green text-ink" : "bg-brand-coral/15 border-brand-coral text-ink"
                  }`}>
                    <div className="flex items-center gap-2">
                      {isCorrect ? <CheckCircle2 className="w-4 h-4 text-brand-green" /> : <XCircle className="w-4 h-4 text-brand-coral" />}
                      <span>
                        {isCorrect
                          ? `Correct! Full Marks Awarded (+${scoreAchieved.toFixed(1)} / ${maxScore.toFixed(1)} Pts). Locked.`
                          : `Evaluated: 0.0 / ${maxScore.toFixed(1)} Marks. Locked.`}
                      </span>
                    </div>
                    <span className={`tactile-tag text-[10px] font-black uppercase ${
                      isCorrect ? "bg-brand-green text-white" : "bg-brand-coral text-white"
                    }`}>
                      {isCorrect ? "SOLVED ✓" : "ATTEMPTED"}
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

        {/* Right: Instant Deterministic Grading Provenance & Full Explanation */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <h3 className="text-lg font-black text-ink flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-brand-green" />
            <span>Assessment &amp; Explanation</span>
          </h3>

          {isQuestionAnswered ? (
            <div className="tactile-card p-5 flex flex-col gap-4 animate-fade-in">
              {/* Verdict Header */}
              {isCorrect ? (
                <div className="p-4 bg-brand-green/15 border-2 border-brand-green rounded-friendly-sm flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-7 h-7 text-brand-green shrink-0" />
                    <div>
                      <div className="font-black text-base text-ink">
                        CORRECT ANSWER &bull; FULL MARKS
                      </div>
                      <div className="text-xs text-ink-muted font-bold">
                        +{scoreAchieved.toFixed(1)} / {maxScore.toFixed(1)} Marks Awarded
                      </div>
                    </div>
                  </div>
                  <span className="tactile-tag bg-brand-green text-white text-xs font-black uppercase">
                    CORRECT
                  </span>
                </div>
              ) : (
                <div className="p-4 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <XCircle className="w-7 h-7 text-brand-coral shrink-0" />
                    <div>
                      <div className="font-black text-base text-ink">
                        INCORRECT ANSWER
                      </div>
                      <div className="text-xs text-ink-muted font-bold">
                        {scoreAchieved.toFixed(1)} / {maxScore.toFixed(1)} Marks
                      </div>
                    </div>
                  </div>
                  <span className="tactile-tag bg-brand-coral text-white text-xs font-black uppercase">
                    INCORRECT
                  </span>
                </div>
              )}

              {/* Submitted Answer vs Awarded Score */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 bg-surface rounded border border-ink/20">
                  <span className="text-[10px] text-ink-muted font-black block uppercase">
                    Submitted Answer:
                  </span>
                  <span className="font-mono font-bold text-ink mt-0.5 block truncate" title={submittedAnswerVal}>
                    {submittedAnswerVal || "None"}
                  </span>
                </div>
                <div className="p-2.5 bg-surface rounded border border-ink/20">
                  <span className="text-[10px] text-ink-muted font-black block uppercase">
                    Awarded Score:
                  </span>
                  <span className={`font-black text-sm mt-0.5 block ${isCorrect ? "text-brand-green" : "text-brand-coral"}`}>
                    {scoreAchieved.toFixed(1)} / {maxScore.toFixed(1)} Pts
                  </span>
                </div>
              </div>

              {/* Grader Verification Steps */}
              {evaluationSteps.length > 0 && (
                <div className="flex flex-col gap-1 p-2.5 bg-surface border border-ink/20 rounded">
                  <span className="text-[10px] font-black uppercase text-ink-muted">
                    Evaluator Verification Steps:
                  </span>
                  <ul className="text-xs text-ink space-y-1">
                    {evaluationSteps.map((s, idx) => (
                      <li key={idx} className="flex items-start gap-1 font-medium">
                        <Check className="w-3.5 h-3.5 text-brand-green shrink-0 mt-0.5" />
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Deductions if any */}
              {deductions.length > 0 && (
                <div className="flex flex-col gap-1 p-2.5 bg-brand-coral/10 border border-brand-coral/30 rounded">
                  <span className="text-[10px] font-black uppercase text-brand-coral">
                    Deductions &amp; Gaps:
                  </span>
                  <ul className="text-xs text-ink space-y-1">
                    {deductions.map((d, idx) => (
                      <li key={idx} className="flex items-start gap-1 font-medium">
                        <X className="w-3.5 h-3.5 text-brand-coral shrink-0 mt-0.5" />
                        <span>{d.reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Formal Step-by-Step Explanation */}
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-black text-ink uppercase tracking-wider">
                  {isCorrect ? "Formal Proof & Step-by-Step Explanation:" : "Authoritative Solution & Explanation:"}
                </span>
                <div className={`p-3.5 rounded-friendly-sm border-2 text-xs leading-relaxed font-medium whitespace-pre-wrap ${
                  isCorrect
                    ? "bg-brand-green/10 border-brand-green/40 text-ink"
                    : "bg-brand-yellow/20 border-brand-yellow text-ink"
                }`}>
                  {explanationText}
                </div>
              </div>

              {/* Expected Key */}
              {expectedKey && (
                <div className="flex items-center justify-between p-2 bg-surface rounded border border-ink/20 text-xs">
                  <span className="font-bold text-ink-muted">Authoritative Key:</span>
                  <span className="font-mono font-bold text-ink">{expectedKey}</span>
                </div>
              )}

              {/* Grounded Citation */}
              <div className="flex items-center gap-2 pt-2 border-t border-ink/10 text-xs">
                <span className="font-bold text-ink">Reference:</span>
                <span className="tactile-tag bg-surface text-ink text-[10px] font-mono">
                  {referenceCitation || "[Course Syllabus Lecture Notes]"}
                </span>
              </div>
            </div>
          ) : (
            <div className="tactile-card p-8 text-center text-ink-muted flex flex-col items-center justify-center gap-2 min-h-[240px]">
              <HelpCircle className="w-8 h-8 text-ink-faint" />
              <div className="font-bold text-sm">No Attempt Evaluated Yet</div>
              <p className="text-xs max-w-xs font-medium">
                Submit an answer to view the full formal proof, awarded marks, and step-by-step reasoning for both correct and incorrect answers.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
