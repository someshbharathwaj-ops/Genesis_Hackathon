"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  FileCheck2,
  HelpCircle,
  Layers,
  Lock,
  Play,
  RotateCcw,
  SearchCheck,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";
import {
  AssessmentContext,
  AttemptCreate,
  AttemptResponse,
  CourseResponse,
  LearningObjectiveResponse,
  QuestionResponse,
  RevisorReviewResponse,
  TopicResponse,
  UserResponse,
} from "../types";
import { ApiError, recallApi } from "../lib/api-client";

export interface AdaptiveNextRecommendation {
  type: "mastery_advance" | "prerequisite_reinforce" | "alternative_practice" | "track_completed";
  badge: string;
  badgeColor: string;
  reason: string;
  targetObjective: LearningObjectiveResponse;
  question: QuestionResponse;
}

interface RevisorTabProps {
  course: CourseResponse | null;
  topics: TopicResponse[];
  currentUser: UserResponse | null;
  hasActiveScoredAssessment: boolean;
  onToggleLockout?: () => void;
  targetObjective?: LearningObjectiveResponse | null;
}

export function RevisorTab({
  course,
  topics,
  currentUser,
  hasActiveScoredAssessment,
  onToggleLockout,
  targetObjective,
}: RevisorTabProps) {
  const [subView, setSubView] = useState<"practice" | "audit" | "schedule">("practice");

  // --- PRACTICE & ASSESSMENT STATE ---
  const [questions, setQuestions] = useState<QuestionResponse[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionResponse | null>(null);
  const [loadingQuestions, setLoadingQuestions] = useState<boolean>(false);
  const [selectedTopicId, setSelectedTopicId] = useState<string>("ALL");
  const [selectedObjectiveId, setSelectedObjectiveId] = useState<string>("");
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all");
  const [assessmentContext, setAssessmentContext] =
    useState<AssessmentContext>("unscored_practice");
  const [answerInput, setAnswerInput] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submissionResult, setSubmissionResult] = useState<AttemptResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // --- ADAPTIVE COMPLETION & PROGRESSION STATE ---
  const [completedQuestionIds, setCompletedQuestionIds] = useState<string[]>([]);
  const [nextAdaptiveRecommendation, setNextAdaptiveRecommendation] =
    useState<AdaptiveNextRecommendation | null>(null);
  const [preparingAdaptiveNext, setPreparingAdaptiveNext] = useState<boolean>(false);

  const storageKey = `recall_completed_questions_${currentUser?.id || "anon"}_${course?.id || "default"}`;

  // Load completed questions from localStorage on mount / course switch
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

  // --- EXPLANATION AUDIT STATE ---
  const [candidateText, setCandidateText] = useState<string>(
    "Given R(A, B, C, D) with F = {A -> B, B -> C}, attribute closure {A}+ includes {A, B, C} via transitivity."
  );
  const [queryTopic, setQueryTopic] = useState<string>("Transitive functional dependencies");
  const [auditObjectiveId, setAuditObjectiveId] = useState<string>("");
  const [auditQuestionId, setAuditQuestionId] = useState<string>("");
  const [checkDeterministicLogic, setCheckDeterministicLogic] = useState<boolean>(true);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [reviewResult, setReviewResult] = useState<RevisorReviewResponse | null>(null);
  const [auditLockoutError, setAuditLockoutError] = useState<string | null>(null);
  const [auditErrorMsg, setAuditErrorMsg] = useState<string | null>(null);

  // Flatten objectives for selectors
  const allObjectives: LearningObjectiveResponse[] = topics.flatMap((t) => t.objectives);

  const displayedObjectives =
    selectedTopicId === "ALL"
      ? allObjectives
      : (topics.find((t) => t.id === selectedTopicId)?.objectives || allObjectives);

  // Dynamic sample claims tailored to question
  const getClaims = (q: QuestionResponse | null) => {
    if (!q) {
      if (course?.code === "CS301") {
        return {
          valid: "Deadlock occurs if and only if Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait all hold simultaneously.",
          contradiction: "Breaking mutual exclusion alone is insufficient; all four Coffman conditions must be broken to prevent deadlock.",
          ungrounded: "Quantum entanglement between threads eliminates CPU scheduling context switch delays."
        };
      }
      return {
        valid: "Given R(A, B, C, D) with F = {A -> B, B -> C}, attribute closure {A}+ includes {A, B, C} via transitivity.",
        contradiction: "Under Armstrong axioms, the closure of {A} under A -> B unconditionally contains {A, B, C, D}.",
        ungrounded: "Quantum database qubits replace classical primary keys to optimize Bell states."
      };
    }
    const t = q.title.toLowerCase();
    const v = q.versions[0];
    if (t.includes("deadlock") || t.includes("coffman")) {
      return {
        valid: "Deadlock can occur if and only if all four Coffman conditions hold: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.",
        contradiction: "A single directed cycle in a multi-instance resource graph is a sufficient guarantee that deadlock has occurred.",
        ungrounded: "Cosmic microwave background noise automatically arbitrates resource lock acquisition."
      };
    } else if (t.includes("scheduling") || t.includes("sjf") || t.includes("srtf")) {
      return {
        valid: "Shortest Job First provably minimizes average waiting time by scheduling the process with the shortest CPU burst first.",
        contradiction: "First-Come First-Served scheduling provably minimizes average waiting time across all arbitrary burst workloads.",
        ungrounded: "Warp speed thread execution removes all CPU burst time calculation requirements."
      };
    } else if (t.includes("synchronization") || t.includes("peterson") || t.includes("semaphore")) {
      return {
        valid: "Peterson's solution guarantees mutual exclusion, progress, and bounded waiting using shared flag and turn variables.",
        contradiction: "Peterson's solution allows both processes to simultaneously enter their critical sections whenever turn is equal to 0.",
        ungrounded: "Telepathic bus snooping eliminates race conditions without atomic instructions."
      };
    } else if (t.includes("paging") || t.includes("tlb") || t.includes("memory")) {
      return {
        valid: "Paging divides logical memory into fixed-size pages and physical memory into frames, eliminating external fragmentation.",
        contradiction: "Paging suffers from severe external fragmentation because variable-length allocations fragment free physical frames.",
        ungrounded: "Sub-atomic liquid RAM bypasses page table address translation."
      };
    } else if (t.includes("closure")) {
      return {
        valid: "Attribute closure {X}+ iteratively collects all attributes determined by functional dependencies in F starting from X.",
        contradiction: "Attribute closure can only remove attributes from the starting set and can never derive new attributes.",
        ungrounded: "Blockchain consensus algorithms compute relational attribute closures."
      };
    }
    return {
      valid: v?.explanation ? v.explanation.slice(0, 150) : `In ${q.title}, the formal property verified in syllabus lecture notes holds strictly.`,
      contradiction: `In ${q.title}, the opposite condition holds contrary to standard syllabus definitions.`,
      ungrounded: `Speculative dark matter compute governs ${q.title}.`
    };
  };

  // Initialize selected objective
  useEffect(() => {
    if (targetObjective) {
      setSelectedObjectiveId(targetObjective.id);
      setAuditObjectiveId(targetObjective.id);
    } else if (allObjectives.length > 0 && !selectedObjectiveId) {
      setSelectedObjectiveId(allObjectives[0].id);
      setAuditObjectiveId(allObjectives[0].id);
    }
  }, [targetObjective, allObjectives]);

  // Load questions when objective changes
  useEffect(() => {
    async function loadQuestions() {
      if (!selectedObjectiveId) return;
      setLoadingQuestions(true);
      try {
        const qs = await recallApi.listQuestionsForObjective(selectedObjectiveId);
        setQuestions(qs);
        // Prioritize uncompleted questions so previously answered questions do not repeat
        const uncompleted = qs.filter((q) => !completedQuestionIds.includes(q.id));
        if (uncompleted.length > 0) {
          setSelectedQuestion(uncompleted[0]);
          setSubmissionResult(null);
          setAnswerInput("");
          setNextAdaptiveRecommendation(null);
        } else if (qs.length > 0) {
          setSelectedQuestion(qs[0]);
        } else {
          setSelectedQuestion(null);
        }
      } catch {
        setQuestions([]);
        setSelectedQuestion(null);
      } finally {
        setLoadingQuestions(false);
      }
    }
    loadQuestions();
  }, [selectedObjectiveId, completedQuestionIds.length]);

  // Adaptive next question preparation based on student's submitted answer
  const prepareAdaptiveNext = async (
    resp: AttemptResponse,
    currentQuestion: QuestionResponse,
    updatedCompleted: string[]
  ) => {
    setPreparingAdaptiveNext(true);
    try {
      const isCorrect = resp.is_correct || resp.score_achieved >= (resp.max_possible_score || 1.0) * 0.7;
      const currentObj = allObjectives.find((o) => o.id === currentQuestion.objective_id);

      if (isCorrect) {
        // CASE 1: Student is Correct -> Advance along DAG or to next objective challenge
        // A. Check if there are other uncompleted questions in the same objective
        const sameObjRemaining = questions.filter(
          (q) => q.id !== currentQuestion.id && !updatedCompleted.includes(q.id)
        );
        if (sameObjRemaining.length > 0) {
          setNextAdaptiveRecommendation({
            type: "mastery_advance",
            badge: "MASTERY DEMONSTRATED (+1.0)",
            badgeColor: "bg-brand-green text-white",
            reason: `Excellent answer! Concept mastery verified. Progressing to next challenge in '${currentObj?.title || "this objective"}'.`,
            targetObjective: currentObj || allObjectives[0],
            question: sameObjRemaining[0],
          });
          return;
        }

        // B. If current objective is complete, advance to the NEXT Learning Objective in the DAG!
        const currentIdx = allObjectives.findIndex((o) => o.id === currentObj?.id);
        const subsequentObjectives = allObjectives.slice(currentIdx + 1);

        for (const nextObj of subsequentObjectives) {
          const nextQs = await recallApi.listQuestionsForObjective(nextObj.id);
          const uncompleted = nextQs.filter((q) => !updatedCompleted.includes(q.id));
          if (uncompleted.length > 0) {
            setNextAdaptiveRecommendation({
              type: "mastery_advance",
              badge: "DAG ADVANCEMENT",
              badgeColor: "bg-brand-cyan text-ink",
              reason: `All questions in '${currentObj?.title}' mastered! Advancing along the curriculum DAG to next objective: '${nextObj.title}' (${nextObj.code}).`,
              targetObjective: nextObj,
              question: uncompleted[0],
            });
            return;
          }
        }
      } else {
        // CASE 2: Student is Incorrect -> Diagnosed Gap / Reinforce Prerequisite
        // A. Check if the current objective has prerequisites in the DAG
        const prereqRefs = currentObj?.prerequisite_objective_ids || [];
        for (const pRef of prereqRefs) {
          const prereqObj = allObjectives.find(
            (o) => o.id === pRef || o.code.toUpperCase() === pRef.toUpperCase()
          );
          if (prereqObj) {
            const prereqQs = await recallApi.listQuestionsForObjective(prereqObj.id);
            const uncompletedPrereq = prereqQs.filter((q) => !updatedCompleted.includes(q.id));
            if (uncompletedPrereq.length > 0) {
              setNextAdaptiveRecommendation({
                type: "prerequisite_reinforce",
                badge: "PREREQUISITE REINFORCEMENT",
                badgeColor: "bg-brand-coral text-white",
                reason: `Misconception detected. Adaptive engine recommends reinforcing foundational prerequisite: '${prereqObj.title}' (${prereqObj.code}).`,
                targetObjective: prereqObj,
                question: uncompletedPrereq[0],
              });
              return;
            }
          }
        }

        // B. If no uncompleted prerequisite question, provide alternative uncompleted item in same objective
        const sameObjRemaining = questions.filter(
          (q) => q.id !== currentQuestion.id && !updatedCompleted.includes(q.id)
        );
        if (sameObjRemaining.length > 0) {
          setNextAdaptiveRecommendation({
            type: "prerequisite_reinforce",
            badge: "CONCEPT REINFORCEMENT",
            badgeColor: "bg-brand-yellow text-ink",
            reason: `Incorrect answer. Presenting alternative practice question to reinforce understanding of '${currentObj?.title}'.`,
            targetObjective: currentObj || allObjectives[0],
            question: sameObjRemaining[0],
          });
          return;
        }
      }

      // Fallback: Find ANY uncompleted question across the course curriculum
      for (const anyObj of allObjectives) {
        const anyQs = await recallApi.listQuestionsForObjective(anyObj.id);
        const uncompleted = anyQs.filter((q) => !updatedCompleted.includes(q.id));
        if (uncompleted.length > 0) {
          setNextAdaptiveRecommendation({
            type: "alternative_practice",
            badge: "ADAPTIVE ROTATION",
            badgeColor: "bg-surface text-ink",
            reason: `Continuing curriculum sequence with next available question in '${anyObj.title}'.`,
            targetObjective: anyObj,
            question: uncompleted[0],
          });
          return;
        }
      }

      // If all questions in the entire course are completed
      setNextAdaptiveRecommendation(null);
    } catch {
      setNextAdaptiveRecommendation(null);
    } finally {
      setPreparingAdaptiveNext(false);
    }
  };

  // Submit Answer to Grader
  const handleSubmitAttempt = async () => {
    if (!currentUser || !selectedQuestion || !selectedQuestion.versions[0]) return;
    if (completedQuestionIds.includes(selectedQuestion.id)) return; // Prevent double submit

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmissionResult(null);

    const idempotencyKey = `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
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

      // Lock question from re-submitting and prevent it from appearing again
      const nextCompleted = Array.from(new Set([...completedQuestionIds, selectedQuestion.id]));
      setCompletedQuestionIds(nextCompleted);
      try {
        localStorage.setItem(storageKey, JSON.stringify(nextCompleted));
      } catch {}

      // Prepare next question adaptively based on the answer
      await prepareAdaptiveNext(resp, selectedQuestion, nextCompleted);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Failed to grade attempt.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Apply Adaptive Recommendation: switch to the prepared question
  const handleApplyAdaptiveRecommendation = (rec: AdaptiveNextRecommendation) => {
    if (rec.targetObjective.id !== selectedObjectiveId) {
      setSelectedObjectiveId(rec.targetObjective.id);
    }
    setSelectedQuestion(rec.question);
    setAnswerInput("");
    setSubmissionResult(null);
    setSubmitError(null);
    setNextAdaptiveRecommendation(null);
  };

  // Reset Progress Handler: allow re-attempting questions if student desires
  const handleResetProgress = () => {
    if (window.confirm("Reset solved question records for this course to practice again from the beginning?")) {
      setCompletedQuestionIds([]);
      try {
        localStorage.removeItem(storageKey);
      } catch {}
      setSubmissionResult(null);
      setAnswerInput("");
      setNextAdaptiveRecommendation(null);
      if (questions.length > 0) {
        setSelectedQuestion(questions[0]);
      }
    }
  };

  // Run Revisor Explanation Audit
  const handleRunAudit = async () => {
    if (!course || !currentUser || !candidateText.trim()) return;

    if (hasActiveScoredAssessment) {
      setAuditLockoutError(
        "Revisor evidence reviews are strictly locked out during active scored assessments (ADR 0002)."
      );
      setReviewResult(null);
      return;
    }

    setIsAuditing(true);
    setAuditLockoutError(null);
    setAuditErrorMsg(null);
    setReviewResult(null);

    try {
      const resp = await recallApi.reviewExplanation(
        course.id,
        currentUser.id,
        candidateText,
        queryTopic,
        auditObjectiveId || undefined,
        checkDeterministicLogic
      );
      setReviewResult(resp);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.problem.code === "ASSESSMENT_LOCKOUT") {
        setAuditLockoutError(err.problem.detail);
      } else {
        setAuditErrorMsg(err instanceof Error ? err.message : "Revisor audit failed.");
      }
    } finally {
      setIsAuditing(false);
    }
  };

  const setSampleClaim = (type: "valid" | "contradiction" | "ungrounded") => {
    const targetQ = questions.find((q) => q.id === auditQuestionId) || selectedQuestion;
    const claims = getClaims(targetQ);
    if (type === "valid") {
      setCandidateText(claims.valid);
      setQueryTopic(targetQ ? targetQ.title : "Verified Syllabus Concepts");
    } else if (type === "contradiction") {
      setCandidateText(claims.contradiction);
      setQueryTopic(targetQ ? `${targetQ.title} (Contradiction)` : "Contradiction Check");
    } else {
      setCandidateText(claims.ungrounded);
      setQueryTopic("Ungrounded Speculation");
    }
  };

  if (!course) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <BookOpen className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">Select a course to access Revisor Mode.</p>
      </div>
    );
  }

  const currentVersion = selectedQuestion?.versions[0];
  const activeObj = allObjectives.find((o) => o.id === selectedObjectiveId);
  const isCurrentQuestionCompleted =
    !!selectedQuestion && completedQuestionIds.includes(selectedQuestion.id);
  const uncompletedQuestions = questions.filter(
    (q) => !completedQuestionIds.includes(q.id)
  );
  const completedInThisObjectiveCount = questions.length - uncompletedQuestions.length;

  return (
    <div className="flex flex-col gap-6">
      {/* Mode Sub-Navigation Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b-2 border-ink/10">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSubView("practice")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              subView === "practice" ? "!bg-brand-coral !text-white !shadow-hard-sm" : ""
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Practice & Exam Questions</span>
          </button>
          <button
            onClick={() => setSubView("audit")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              subView === "audit" ? "!bg-brand-coral !text-white !shadow-hard-sm" : ""
            }`}
          >
            <FileCheck2 className="w-4 h-4" />
            <span>Audit Conceptual Explanation</span>
          </button>
        </div>

        {/* Lockout Controller */}
        {onToggleLockout && (
          <button
            onClick={onToggleLockout}
            className={`tactile-tag cursor-pointer ${
              hasActiveScoredAssessment
                ? "bg-brand-coral text-white"
                : "bg-surface-warm text-ink hover:bg-brand-yellow"
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            <span>
              {hasActiveScoredAssessment
                ? "Active Exam Lockout Engaged"
                : "Toggle Scored Exam Lockout"}
            </span>
          </button>
        )}
      </div>

      {/* Lockout Alert Banner */}
      {(hasActiveScoredAssessment || auditLockoutError) && (
        <div className="tactile-card border-brand-coral bg-brand-coral/15 p-5 flex items-start gap-4 animate-shake">
          <div className="w-9 h-9 rounded-friendly-sm bg-brand-coral text-white flex items-center justify-center shrink-0">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="font-black text-sm text-ink">
              ASSESSMENT LOCKOUT ACTIVE: AI Assistance Blocked (ADR 0002)
            </span>
            <p className="text-xs text-ink font-medium leading-relaxed">
              {auditLockoutError ||
                "A scored assessment is actively in progress. Conceptual auditing and Tutor guidance are disabled until submission."}
            </p>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* SUBVIEW 1: PRACTICE & EXAM QUESTIONS                           */}
      {/* ============================================================== */}
      {subView === "practice" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Question Picker & Question Formulation */}
          <div className="lg:col-span-7 flex flex-col gap-5">
            {/* Objective & Context Selection */}
            <div className="tactile-card p-5 flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink/10 pb-3">
                <span className="text-xs font-black uppercase tracking-wider text-ink">
                  Question Setup
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold text-ink-muted">Mode:</span>
                  <select
                    value={assessmentContext}
                    onChange={(e) =>
                      setAssessmentContext(e.target.value as AssessmentContext)
                    }
                    className="tactile-select text-xs py-1 px-2 font-bold"
                  >
                    <option value="unscored_practice">Unscored Practice</option>
                    <option value="independent_checkpoint">Scored Assessment</option>
                  </select>
                </div>
              </div>

              {/* DAG Topic Cluster Filter */}
              {topics.length > 1 && (
                <div className="flex flex-col gap-1.5">
                  <div className="text-xs font-bold text-ink-muted uppercase tracking-wider flex items-center justify-between">
                    <span>Curriculum DAG Cluster:</span>
                    <span className="font-mono text-[10px] text-brand-cyan font-bold">
                      {selectedTopicId === "ALL" ? "All Topics" : topics.find(t => t.id === selectedTopicId)?.code}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      type="button"
                      onClick={() => setSelectedTopicId("ALL")}
                      className={`tactile-btn-white text-[11px] py-1 px-2.5 font-bold ${
                        selectedTopicId === "ALL" ? "!bg-brand-yellow !shadow-hard-sm" : ""
                      }`}
                    >
                      All DAGs ({topics.length})
                    </button>
                    {topics.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => {
                          setSelectedTopicId(t.id);
                          if (t.objectives.length > 0) {
                            setSelectedObjectiveId(t.objectives[0].id);
                          }
                        }}
                        className={`tactile-btn-white text-[11px] py-1 px-2.5 font-bold ${
                          selectedTopicId === t.id ? "!bg-brand-cyan !text-ink !shadow-hard-sm" : ""
                        }`}
                      >
                        DAG #{t.order_index}: {t.code}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Learning Objective Selector */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-ink flex items-center justify-between">
                  <span>Learning Objective:</span>
                  {activeObj?.prerequisite_objective_ids &&
                    activeObj.prerequisite_objective_ids.length > 0 && (
                      <span className="text-[10px] text-ink-muted">
                        Prerequisites: {activeObj.prerequisite_objective_ids.join(", ")}
                      </span>
                    )}
                </label>
                <select
                  value={selectedObjectiveId}
                  onChange={(e) => setSelectedObjectiveId(e.target.value)}
                  className="tactile-select text-xs font-bold"
                >
                  {displayedObjectives.map((obj) => (
                    <option key={obj.id} value={obj.id}>
                      {obj.title} ({obj.code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Question Item Selector */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-ink">Available Questions:</label>
                  <div className="flex items-center gap-2">
                    {completedQuestionIds.length > 0 && (
                      <button
                        type="button"
                        onClick={handleResetProgress}
                        className="text-[10px] text-ink-muted hover:text-brand-coral font-bold underline cursor-pointer"
                        title="Clear completed history for this course"
                      >
                        Reset History
                      </button>
                    )}
                    <span className="tactile-tag bg-surface text-ink text-[10px]">
                      {uncompletedQuestions.length} Pending &bull; {completedInThisObjectiveCount} Solved
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
                      setNextAdaptiveRecommendation(null);
                    }
                  }}
                  className="tactile-select text-xs font-medium"
                >
                  {questions.length === 0 ? (
                    <option value="">No questions found for this objective</option>
                  ) : uncompletedQuestions.length === 0 ? (
                    <option value={selectedQuestion?.id || ""}>
                      All {questions.length} questions in this objective completed! ✓
                    </option>
                  ) : (
                    uncompletedQuestions.map((q) => (
                      <option key={q.id} value={q.id}>
                        {q.title} ({q.question_type}) &bull; {q.versions[0]?.difficulty || "standard"}
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>

            {/* Question Display Card */}
            {selectedQuestion && currentVersion ? (
              <div className="tactile-card p-6 flex flex-col gap-5">
                {/* Completion Status Alert */}
                {isCurrentQuestionCompleted && (
                  <div className="p-3 bg-brand-green/15 border-2 border-brand-green rounded-friendly-sm flex items-center justify-between text-xs font-bold text-ink animate-fade-in">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-brand-green shrink-0" />
                      <span>Answer Submitted &amp; Evaluated &mdash; Submit option is locked for this question.</span>
                    </div>
                    <span className="tactile-tag bg-brand-green text-white text-[10px] uppercase font-black">
                      COMPLETED
                    </span>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-ink/10 pb-3">
                  <div>
                    <h3 className="text-lg font-black text-ink">{selectedQuestion.title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="tactile-tag bg-brand-yellow text-ink text-[10px]">
                        Difficulty: {currentVersion.difficulty}
                      </span>
                      <span className="tactile-tag bg-surface text-ink text-[10px]">
                        Points: {currentVersion.max_score}
                      </span>
                      <span className="tactile-tag bg-brand-cyan/20 text-brand-cyan text-[10px]">
                        Grader: Deterministic Pure Function
                      </span>
                    </div>
                  </div>
                </div>

                {/* Prompt */}
                <div className="p-4 bg-surface rounded-friendly-sm border-2 border-ink text-sm font-medium leading-relaxed text-ink whitespace-pre-wrap">
                  {currentVersion.prompt}
                </div>

                {/* Multiple Choice / Select Clickable Options */}
                {currentVersion.options && currentVersion.options.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-bold text-ink-muted">Select Option:</label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {(currentVersion.options as Array<{ id?: string; text?: string }>).map((opt) => {
                        const optId = String(opt.id || "");
                        const optText = String(opt.text || "");
                        const isChosen =
                          selectedQuestion.question_type === "multiple_select"
                            ? answerInput.toUpperCase().includes(optId.toUpperCase())
                            : answerInput.trim().toUpperCase() === optId.toUpperCase();
                        return (
                          <button
                            key={optId}
                            type="button"
                            disabled={isCurrentQuestionCompleted || isSubmitting}
                            onClick={() => {
                              if (isCurrentQuestionCompleted) return;
                              if (selectedQuestion.question_type === "multiple_select") {
                                const currentParts = answerInput
                                  .split(",")
                                  .map((s) => s.trim().toUpperCase())
                                  .filter(Boolean);
                                const exists = currentParts.includes(optId.toUpperCase());
                                const nextParts = exists
                                  ? currentParts.filter((p) => p !== optId.toUpperCase())
                                  : [...currentParts, optId.toUpperCase()].sort();
                                setAnswerInput(nextParts.join(", "));
                              } else {
                                setAnswerInput(optId);
                              }
                            }}
                            className={`p-3 text-left border-2 border-ink rounded-friendly-sm text-xs transition-all ${
                              isChosen
                                ? "bg-brand-yellow font-black shadow-hard-sm border-ink"
                                : "bg-surface hover:bg-surface-warm font-medium"
                            } ${isCurrentQuestionCompleted ? "cursor-not-allowed opacity-80" : ""}`}
                          >
                            <span className="font-mono font-black mr-2 bg-ink/10 px-1.5 py-0.5 rounded">
                              {optId}
                            </span>
                            <span>{optText}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Answer Submission Form */}
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-ink">Your Answer:</label>
                    <button
                      type="button"
                      onClick={() => {
                        setSubView("audit");
                        setAuditQuestionId(selectedQuestion.id);
                        setAuditObjectiveId(selectedQuestion.objective_id);
                        const claims = getClaims(selectedQuestion);
                        setCandidateText(claims.valid);
                        setQueryTopic(selectedQuestion.title);
                      }}
                      className="tactile-btn-white text-[11px] py-1 px-2.5 flex items-center gap-1.5 font-bold hover:!bg-brand-coral hover:!text-white"
                      title="Audit your conceptual explanation for this exact question"
                    >
                      <FileCheck2 className="w-3.5 h-3.5 text-brand-coral" />
                      <span>Audit Explanation on this Question</span>
                    </button>
                  </div>
                  <input
                    type="text"
                    value={answerInput}
                    onChange={(e) => setAnswerInput(e.target.value)}
                    placeholder={
                      isCurrentQuestionCompleted
                        ? "Answer submitted & evaluated. Question locked."
                        : "Enter answer (or click options above)"
                    }
                    className={`tactile-input text-xs font-mono ${
                      isCurrentQuestionCompleted ? "bg-surface opacity-80 cursor-not-allowed" : ""
                    }`}
                    disabled={isCurrentQuestionCompleted || isSubmitting}
                  />

                  {submitError && (
                    <div className="p-3 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm text-xs font-bold text-ink">
                      {submitError}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <span className="text-[11px] text-ink-muted font-medium">
                      {isCurrentQuestionCompleted
                        ? "Evaluated deterministically. Submit option is locked."
                        : "Evaluated using Armstrong axioms closure computation."}
                    </span>
                    {isCurrentQuestionCompleted ? (
                      <div className="flex items-center gap-2 px-4 py-2 bg-brand-green/20 border-2 border-brand-green rounded-friendly-sm text-xs font-black text-brand-green">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Submitted &amp; Evaluated</span>
                      </div>
                    ) : (
                      <button
                        onClick={handleSubmitAttempt}
                        disabled={isSubmitting || !answerInput.trim()}
                        className="tactile-btn-coral text-xs py-2.5 px-5 font-black"
                      >
                        <Send className={`w-3.5 h-3.5 ${isSubmitting ? "animate-spin" : ""}`} />
                        <span>{isSubmitting ? "Evaluating..." : "Submit Answer"}</span>
                      </button>
                    )}
                  </div>

                  {/* ADAPTIVE NEXT QUESTION CARD */}
                  {nextAdaptiveRecommendation && (
                    <div className="p-4 bg-brand-yellow/20 border-2 border-ink rounded-friendly-sm flex flex-col gap-3 shadow-hard-sm mt-3 animate-fade-in">
                      <div className="flex items-center justify-between">
                        <span className={`tactile-tag text-xs font-black ${nextAdaptiveRecommendation.badgeColor}`}>
                          {nextAdaptiveRecommendation.badge}
                        </span>
                        <span className="text-[10px] font-mono font-bold text-ink-muted uppercase">
                          Adaptive Next Step
                        </span>
                      </div>
                      <div className="flex flex-col gap-1">
                        <div className="text-xs font-black text-ink leading-relaxed">
                          {nextAdaptiveRecommendation.reason}
                        </div>
                        <div className="text-xs text-ink-muted">
                          Next Question: <span className="font-bold text-ink">{nextAdaptiveRecommendation.question.title}</span> &bull; {nextAdaptiveRecommendation.question.question_type}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleApplyAdaptiveRecommendation(nextAdaptiveRecommendation)}
                        className="tactile-btn-yellow text-xs py-2.5 px-4 font-black flex items-center justify-center gap-2 w-full shadow-hard-sm hover:scale-[1.01] transition-transform"
                      >
                        <span>Proceed to Next Adaptive Question</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  )}

                  {preparingAdaptiveNext && (
                    <div className="p-3 bg-surface border border-ink/20 rounded text-xs font-bold text-ink-muted flex items-center gap-2">
                      <div className="w-3.5 h-3.5 border-2 border-brand-yellow border-t-transparent rounded-full animate-spin" />
                      <span>Analyzing answer &amp; preparing next adaptive question...</span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="tactile-card p-8 text-center text-ink-muted">
                <HelpCircle className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
                <p className="font-bold">Select an objective with verified questions.</p>
              </div>
            )}
          </div>

          {/* Right Column: Detailed Explanation & Grading Result */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <h3 className="text-base font-black text-ink flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-brand-green" />
              <span>Assessment & Explanation</span>
            </h3>

            {submissionResult ? (
              <div className="tactile-card p-6 flex flex-col gap-4">
                {/* Result Status Badge */}
                <div className="flex items-center justify-between pb-3 border-b border-ink/10">
                  <span className="text-xs font-bold text-ink-muted">Grading Result:</span>
                  <span
                    className={`tactile-tag text-xs font-black ${
                      submissionResult.is_correct
                        ? "bg-brand-green text-white"
                        : "bg-brand-coral text-white"
                    }`}
                  >
                    {submissionResult.is_correct ? "CORRECT (+1.0)" : "INCORRECT (0.0)"}
                  </span>
                </div>

                {/* Score Summary */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 bg-surface rounded border border-ink/20">
                    <span className="text-[10px] text-ink-muted font-bold block">
                      Submitted Answer:
                    </span>
                    <span className="font-mono font-bold text-ink">
                      {JSON.stringify(submissionResult.submitted_answer)}
                    </span>
                  </div>
                  <div className="p-2.5 bg-surface rounded border border-ink/20">
                    <span className="text-[10px] text-ink-muted font-bold block">
                      Graded Score:
                    </span>
                    <span className="font-bold text-ink">
                      {submissionResult.score_achieved} / {submissionResult.max_possible_score}
                    </span>
                  </div>
                </div>

                {/* Step-by-Step Explanation */}
                <div className="flex flex-col gap-1.5 pt-2">
                  <span className="text-xs font-black text-ink">Step-by-Step Explanation:</span>
                  <div className="p-3 bg-brand-yellow/15 border border-brand-yellow rounded text-xs text-ink leading-relaxed font-medium whitespace-pre-wrap">
                    {currentVersion?.explanation ||
                      "Each dependency was traced through transitivity to compute the complete attribute closure."}
                  </div>
                </div>

                {/* Underlying Concept & Prerequisite */}
                <div className="flex flex-col gap-1.5 pt-2 border-t border-ink/10">
                  <span className="text-xs font-bold text-ink">Underlying Concept:</span>
                  <div className="text-xs text-ink-muted font-medium">
                    {activeObj ? (
                      <>
                        <span className="font-bold text-ink">{activeObj.title}</span> (
                        {activeObj.code}) &mdash; {activeObj.description}
                      </>
                    ) : (
                      "Relational functional dependencies"
                    )}
                  </div>
                </div>

                {/* Grounded Citation */}
                <div className="flex items-center gap-2 pt-2 border-t border-ink/10 text-xs">
                  <span className="font-bold text-ink">Source Reference:</span>
                  <span className="tactile-tag bg-surface text-ink text-[10px]">
                    {String(
                      currentVersion?.answer_key?.reference ||
                        "[Lecture: dbms_functional_dependencies.md, Page 1]"
                    )}
                  </span>
                </div>

                {/* Adaptive Next Question Action in Grading Result */}
                {nextAdaptiveRecommendation && (
                  <div className="p-3.5 bg-brand-yellow/15 border-2 border-ink rounded-friendly-sm flex flex-col gap-2 mt-1">
                    <div className="flex items-center justify-between">
                      <span className={`tactile-tag text-[10px] font-black ${nextAdaptiveRecommendation.badgeColor}`}>
                        {nextAdaptiveRecommendation.badge}
                      </span>
                      <span className="text-[10px] font-mono font-bold text-ink-muted uppercase">Adaptive Sequence</span>
                    </div>
                    <div className="text-xs font-black text-ink leading-tight">
                      {nextAdaptiveRecommendation.reason}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleApplyAdaptiveRecommendation(nextAdaptiveRecommendation)}
                      className="tactile-btn-yellow text-xs py-2 px-3 font-black flex items-center justify-center gap-1.5 w-full mt-1"
                    >
                      <span>Proceed to Next Question</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="tactile-card p-8 text-center text-ink-muted flex flex-col items-center gap-2">
                <Play className="w-8 h-8 text-ink-faint" />
                <p className="font-bold text-xs">
                  Submit an answer to view the deterministic evaluation breakdown, step-by-step
                  reasoning, and concept citation.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* SUBVIEW 2: CONCEPTUAL EXPLANATION AUDIT                        */}
      {/* ============================================================== */}
      {subView === "audit" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Input Sandbox */}
          <div className="lg:col-span-6 flex flex-col gap-4">
            <div className="tactile-card p-5 flex flex-col gap-4">
              <div className="font-black text-sm text-ink flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-brand-coral" />
                <span>Submit Conceptual Explanation for Audit</span>
              </div>

              {/* Target Question Selector for Audit */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-ink">Audit Concept for Question:</label>
                  <span className="text-[10px] text-brand-coral font-bold">
                    {auditQuestionId ? "Linked to Question" : "General Topic Concept"}
                  </span>
                </div>
                <select
                  value={auditQuestionId}
                  onChange={(e) => {
                    const qId = e.target.value;
                    setAuditQuestionId(qId);
                    const found = questions.find((q) => q.id === qId);
                    if (found) {
                      setAuditObjectiveId(found.objective_id);
                      const claims = getClaims(found);
                      setCandidateText(claims.valid);
                      setQueryTopic(found.title);
                    }
                  }}
                  className="tactile-select text-xs font-bold"
                >
                  <option value="">General Topic Concept (No specific question)</option>
                  {questions.map((q) => (
                    <option key={q.id} value={q.id}>
                      {q.title} ({q.question_type})
                    </option>
                  ))}
                </select>
              </div>

              {/* Sample Prompts */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-ink-muted">
                  Quick Sample Claims (Dynamically Tailored to Target Question):
                </label>
                <div className="flex flex-col gap-1.5 text-xs">
                  <button
                    type="button"
                    onClick={() => setSampleClaim("valid")}
                    className="p-2 border border-brand-green/30 rounded bg-brand-green/10 hover:bg-brand-green/20 text-left text-[11px] font-medium"
                  >
                    &quot;{getClaims(questions.find(q => q.id === auditQuestionId) || selectedQuestion).valid}&quot; (Valid)
                  </button>
                  <button
                    type="button"
                    onClick={() => setSampleClaim("contradiction")}
                    className="p-2 border border-brand-coral/40 rounded bg-brand-coral/10 hover:bg-brand-coral/20 text-left text-[11px] font-bold text-brand-coral"
                  >
                    &quot;{getClaims(questions.find(q => q.id === auditQuestionId) || selectedQuestion).contradiction}&quot; (Contradiction)
                  </button>
                  <button
                    type="button"
                    onClick={() => setSampleClaim("ungrounded")}
                    className="p-2 border border-ink/20 rounded bg-surface hover:bg-surface-warm text-left text-[11px] font-medium"
                  >
                    &quot;{getClaims(questions.find(q => q.id === auditQuestionId) || selectedQuestion).ungrounded}&quot; (Ungrounded)
                  </button>
                </div>
              </div>

              {/* DAG Objective Selector */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-ink">Related Curriculum Objective:</label>
                <select
                  value={auditObjectiveId}
                  onChange={(e) => setAuditObjectiveId(e.target.value)}
                  className="tactile-select text-xs font-bold"
                >
                  <option value="">General / None Specified</option>
                  {allObjectives.map((obj) => (
                    <option key={obj.id} value={obj.id}>
                      {obj.title} ({obj.code})
                    </option>
                  ))}
                </select>
              </div>

              {/* Text Input */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-ink">Candidate Explanation:</label>
                <textarea
                  rows={4}
                  value={candidateText}
                  onChange={(e) => setCandidateText(e.target.value)}
                  placeholder="Explain a concept or relationship..."
                  className="tactile-input text-xs font-mono"
                  disabled={isAuditing}
                />
              </div>

              {/* Deterministic Check Toggle */}
              <div className="flex items-center justify-between p-3 bg-surface rounded border border-ink/20">
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-ink">Deterministic Axiom Check</span>
                  <span className="text-[10px] text-ink-muted">
                    Validates closures against Armstrong relational engine
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={checkDeterministicLogic}
                  onChange={(e) => setCheckDeterministicLogic(e.target.checked)}
                  className="w-4 h-4 accent-brand-coral cursor-pointer"
                />
              </div>

              {auditErrorMsg && (
                <div className="p-3 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm text-xs font-bold text-ink">
                  {auditErrorMsg}
                </div>
              )}

              <button
                onClick={handleRunAudit}
                disabled={isAuditing || !candidateText.trim()}
                className="tactile-btn-coral text-xs py-2.5 font-black"
              >
                <SearchCheck className={`w-3.5 h-3.5 ${isAuditing ? "animate-spin" : ""}`} />
                <span>{isAuditing ? "Auditing Against Syllabus..." : "Audit Explanation"}</span>
              </button>
            </div>
          </div>

          {/* Right: Audit Report Output */}
          <div className="lg:col-span-6 flex flex-col gap-4">
            <h3 className="text-base font-black text-ink flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-brand-coral" />
              <span>Revisor Audit Verdict</span>
            </h3>

            {reviewResult ? (
              <div className="tactile-card p-6 flex flex-col gap-5">
                {/* Status Badge */}
                <div className="flex items-center justify-between pb-3 border-b border-ink/10">
                  <span className="text-xs font-bold text-ink-muted">Audit Verdict:</span>
                  <span
                    className={`tactile-tag text-xs font-black ${
                      reviewResult.audit_status === "verified_grounded"
                        ? "bg-brand-green text-white"
                        : reviewResult.audit_status === "contradiction_detected"
                        ? "bg-brand-coral text-white"
                        : "bg-brand-yellow text-ink"
                    }`}
                  >
                    {reviewResult.audit_status.toUpperCase()}
                  </span>
                </div>

                {/* Summary */}
                <div className="p-3.5 bg-surface rounded border border-ink/20 text-xs font-medium text-ink leading-relaxed">
                  {reviewResult.summary}
                </div>

                {/* Verified Points */}
                {reviewResult.verified_points && reviewResult.verified_points.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-black text-brand-green">Verified Assertions:</span>
                    <ul className="list-disc list-inside text-xs text-ink space-y-1">
                      {reviewResult.verified_points.map((pt, i) => (
                        <li key={i}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Flagged Issues */}
                {reviewResult.flagged_issues && reviewResult.flagged_issues.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-black text-brand-coral">Flagged Issues:</span>
                    <ul className="list-disc list-inside text-xs text-brand-coral space-y-1">
                      {reviewResult.flagged_issues.map((iss, i) => (
                        <li key={i}>{iss}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Citations */}
                {reviewResult.citations_verified && reviewResult.citations_verified.length > 0 && (
                  <div className="flex flex-col gap-1.5 pt-2 border-t border-ink/10">
                    <span className="text-xs font-bold text-ink">Verified Syllabus Citations:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {reviewResult.citations_verified.map((cit, i) => (
                        <span key={i} className="tactile-tag bg-surface text-ink text-[10px]">
                          {cit}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="tactile-card p-8 text-center text-ink-muted">
                <SearchCheck className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
                <p className="font-bold text-xs">
                  Submit an explanation to see the Revisor audit report with exact citations and
                  contradiction checks.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
