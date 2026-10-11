"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Award,
  BookOpen,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCheck2,
  Flame,
  HelpCircle,
  History,
  Layers,
  Lock,
  Play,
  RotateCcw,
  SearchCheck,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
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
  RevisorReviewResponse,
  TopicResponse,
  UserResponse,
} from "../types";
import { ApiError, recallApi } from "../lib/api-client";

export interface QuestionAttemptRecord {
  questionId: string;
  questionTitle: string;
  objectiveId?: string;
  objectiveTitle?: string;
  isCorrect: boolean;
  scoreAchieved: number;
  maxScore: number;
  submittedAnswer: Record<string, unknown> | string;
  explanation: string;
  evaluationSteps?: string[];
  deductions?: Array<{ reason: string; [key: string]: unknown }>;
  referenceCitation?: string;
  expectedKey?: string;
  timestamp: string;
}

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

  // --- ATTEMPT HISTORY & MARKS TRACKING STATE ---
  const [attemptHistory, setAttemptHistory] = useState<Record<string, QuestionAttemptRecord>>({});
  const [showMarksLedger, setShowMarksLedger] = useState<boolean>(false);

  const storageKey = `recall_completed_questions_${currentUser?.id || "anon"}_${course?.id || "default"}`;
  const historyStorageKey = `recall_attempt_history_${currentUser?.id || "anon"}_${course?.id || "default"}`;

  // Load completed questions & full attempt records from localStorage and backend
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

    // Also sync from backend attempts if user is logged in
    if (currentUser?.id) {
      recallApi.listStudentAttempts(currentUser.id).then((attempts) => {
        if (attempts && attempts.length > 0) {
          setAttemptHistory((prev) => {
            const updated = { ...prev };
            attempts.forEach((att) => {
              if (!updated[att.question_id]) {
                updated[att.question_id] = {
                  questionId: att.question_id,
                  questionTitle: `Question (${att.question_id.slice(0, 8)})`,
                  isCorrect: att.is_correct,
                  scoreAchieved: att.score_achieved,
                  maxScore: att.max_possible_score || 1.0,
                  submittedAnswer: att.submitted_answer,
                  explanation: "Verified against authoritative course rubric.",
                  evaluationSteps: (att.grading_provenance?.evaluation_steps as string[]) || [],
                  deductions: (att.grading_provenance?.deductions as any[]) || [],
                  referenceCitation: String(att.grading_provenance?.expected_answer_ref || ""),
                  timestamp: att.created_at ? String(att.created_at) : new Date().toISOString(),
                };
              }
            });
            try {
              localStorage.setItem(historyStorageKey, JSON.stringify(updated));
            } catch {}
            return updated;
          });
          setCompletedQuestionIds((prev) =>
            Array.from(new Set([...prev, ...attempts.map((a) => a.question_id)]))
          );
        }
      }).catch(() => {});
    }
  }, [storageKey, historyStorageKey, currentUser?.id]);

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
      const currentObj = allObjectives.find((o) => o.id === currentQuestion.objective_id);

      // 1. Authoritative Backend Adaptive Decision (POST /api/v1/diagnosis/session/plan)
      if (currentUser?.id && course?.id) {
        try {
          const plan = await recallApi.planDiagnosticSession(
            currentUser.id,
            course.id,
            currentQuestion.objective_id
          );
          if (plan && plan.recommended_questions && plan.recommended_questions.length > 0) {
            const candidate =
              plan.recommended_questions.find(
                (pq) => pq.question_id !== currentQuestion.id && !updatedCompleted.includes(pq.question_id)
              ) ||
              plan.recommended_questions.find((pq) => pq.question_id !== currentQuestion.id) ||
              plan.recommended_questions[0];

            if (candidate) {
              const fullQ = await recallApi.getQuestion(candidate.question_id);
              const targetObj =
                allObjectives.find((o) => o.id === candidate.objective_id) ||
                allObjectives.find((o) => o.code === candidate.objective_code) ||
                currentObj ||
                allObjectives[0];

              if (fullQ) {
                const isPrereq = candidate.priority_reason.toLowerCase().includes("prerequisite");
                setNextAdaptiveRecommendation({
                  type: isPrereq ? "prerequisite_reinforce" : "mastery_advance",
                  badge: `BACKEND ADAPTIVE PROBE • ${candidate.objective_code} (${candidate.difficulty.toUpperCase()})`,
                  badgeColor: isPrereq ? "bg-brand-coral text-white" : "bg-brand-yellow text-ink",
                  reason: `${candidate.priority_reason}. Authoritative Rationale: ${plan.session_rationale}`,
                  targetObjective: targetObj,
                  question: fullQ,
                });
                return;
              }
            }
          }
        } catch (planErr) {
          console.warn("Backend adaptive planner fallback to DAG:", planErr);
        }
      }

      // 2. Client-side DAG fallback if planner unreached
      const isCorrect = resp.is_correct || resp.score_achieved >= (resp.max_possible_score || 1.0) * 0.7;

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
        objectiveTitle: activeObj?.title,
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

      // Save into attemptHistory and localStorage
      setAttemptHistory((prev) => {
        const next = { ...prev, [selectedQuestion.id]: newRecord };
        try {
          localStorage.setItem(historyStorageKey, JSON.stringify(next));
        } catch {}
        return next;
      });

      // Lock question from re-submitting and mark completed
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
    const existingRec = attemptHistory[rec.question.id];
    setAnswerInput(existingRec ? (typeof existingRec.submittedAnswer === "object" ? JSON.stringify(existingRec.submittedAnswer) : String(existingRec.submittedAnswer)) : "");
    setSubmissionResult(null);
    setSubmitError(null);
    setNextAdaptiveRecommendation(null);
  };

  // Reset Progress Handler: allow re-attempting questions if student desires
  const handleResetProgress = () => {
    if (
      window.confirm(
        "Reset solved question records and marks for this course to practice again from the beginning?"
      )
    ) {
      setCompletedQuestionIds([]);
      setAttemptHistory({});
      try {
        localStorage.removeItem(storageKey);
        localStorage.removeItem(historyStorageKey);
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
      {subView === "practice" && (() => {
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
            {/* ============================================================== */}
            {/* LIVE MARKS & PERFORMANCE TRACKER SCOREBOARD                     */}
            {/* ============================================================== */}
            <div className="tactile-card p-4 sm:p-5 bg-surface border-2 border-ink flex flex-col gap-4 shadow-hard-sm animate-fade-in">
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
                      Your Performance &amp; Evaluation Scoreboard
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
                  <button
                    type="button"
                    onClick={() => setShowMarksLedger((prev) => !prev)}
                    className="tactile-btn-white text-xs py-1.5 px-3 font-bold flex items-center gap-1.5 hover:!bg-brand-yellow"
                  >
                    <History className="w-3.5 h-3.5" />
                    <span>{showMarksLedger ? "Hide Marks Ledger" : "View Marks Ledger"}</span>
                    {showMarksLedger ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>
                  {attemptList.length > 0 && (
                    <button
                      type="button"
                      onClick={handleResetProgress}
                      className="text-xs font-bold text-ink-muted hover:text-brand-coral underline py-1 px-2"
                      title="Reset all attempts and marks for this course"
                    >
                      Reset All
                    </button>
                  )}
                </div>
              </div>

              {/* Key Metric Gauges */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {/* 1. Marks Earned */}
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
                    {totalMarksPossible > 0
                      ? `${((totalMarksEarned / totalMarksPossible) * 100).toFixed(0)}% points achieved`
                      : "No questions completed yet"}
                  </span>
                </div>

                {/* 2. Grade & Accuracy */}
                <div className="p-3 bg-surface border-2 border-ink rounded-friendly-sm flex flex-col gap-1">
                  <div className="flex items-center justify-between text-[11px] font-black text-ink-muted uppercase">
                    <span>Accuracy &amp; Grade</span>
                    <Target className="w-4 h-4 text-brand-cyan" />
                  </div>
                  <div className="text-2xl font-black text-ink">
                    {accuracyPercentage}%
                  </div>
                  {/* Progress bar */}
                  <div className="w-full bg-ink/10 h-2 rounded-full overflow-hidden mt-1 border border-ink/20">
                    <div
                      className={`h-full transition-all duration-500 ${
                        accuracyPercentage >= 80
                          ? "bg-brand-green"
                          : accuracyPercentage >= 60
                          ? "bg-brand-yellow"
                          : "bg-brand-coral"
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, accuracyPercentage))}%` }}
                    />
                  </div>
                </div>

                {/* 3. Questions Solved */}
                <div className="p-3 bg-surface border-2 border-ink rounded-friendly-sm flex flex-col gap-1">
                  <div className="flex items-center justify-between text-[11px] font-black text-ink-muted uppercase">
                    <span>Questions Solved</span>
                    <CheckCircle2 className="w-4 h-4 text-brand-green" />
                  </div>
                  <div className="text-2xl font-black text-ink">
                    {attemptList.length}{" "}
                    <span className="text-sm font-bold text-ink-muted">
                      ({correctCount} correct &bull; {attemptList.length - correctCount} wrong)
                    </span>
                  </div>
                  <span className="text-[10px] text-ink-muted font-medium">
                    {completedInThisObjectiveCount} solved in active objective
                  </span>
                </div>

                {/* 4. Active Streak */}
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
                    {streakCount >= 3 ? "🔥 Mastery streak unlocked!" : "Answer correctly to build streak"}
                  </span>
                </div>
              </div>

              {/* Interactive Marks Ledger Drawer */}
              {showMarksLedger && (
                <div className="mt-2 border-2 border-ink rounded-friendly-sm bg-surface-warm p-4 flex flex-col gap-3 animate-fade-in">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-black text-ink uppercase tracking-wider flex items-center gap-2">
                      <History className="w-4 h-4 text-brand-coral" />
                      <span>Itemized Marks Ledger &amp; Question History</span>
                    </h4>
                    <span className="text-[11px] text-ink-muted font-bold">
                      {attemptList.length} recorded item{attemptList.length === 1 ? "" : "s"}
                    </span>
                  </div>

                  {attemptList.length === 0 ? (
                    <div className="p-4 text-center text-xs text-ink-muted font-medium bg-surface rounded border border-ink/10">
                      No questions answered yet. Submit answers below to record marks and build your score history!
                    </div>
                  ) : (
                    <div className="overflow-x-auto max-h-64 overflow-y-auto border border-ink/20 rounded bg-surface">
                      <table className="w-full text-xs text-left border-collapse">
                        <thead className="bg-ink/5 border-b border-ink/10 text-[10px] font-black uppercase text-ink-muted sticky top-0">
                          <tr>
                            <th className="p-2.5">Question Title</th>
                            <th className="p-2.5">Objective</th>
                            <th className="p-2.5">Answer Submitted</th>
                            <th className="p-2.5 text-center">Marks Earned</th>
                            <th className="p-2.5 text-center">Result</th>
                            <th className="p-2.5 text-right">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-ink/10">
                          {sortedAttempts.map((att) => (
                            <tr key={att.questionId} className="hover:bg-surface-warm transition-colors">
                              <td className="p-2.5 font-bold text-ink max-w-[200px] truncate" title={att.questionTitle}>
                                {att.questionTitle}
                              </td>
                              <td className="p-2.5 text-ink-muted text-[11px] max-w-[140px] truncate">
                                {att.objectiveTitle || "Topic LO"}
                              </td>
                              <td className="p-2.5 font-mono text-[11px] text-ink max-w-[120px] truncate" title={String(att.submittedAnswer)}>
                                {typeof att.submittedAnswer === "object" ? JSON.stringify(att.submittedAnswer) : String(att.submittedAnswer)}
                              </td>
                              <td className="p-2.5 text-center font-black">
                                <span
                                  className={`px-2 py-0.5 rounded text-[11px] ${
                                    att.isCorrect
                                      ? "bg-brand-green/20 text-brand-green border border-brand-green/30"
                                      : "bg-brand-coral/20 text-brand-coral border border-brand-coral/30"
                                  }`}
                                >
                                  +{att.scoreAchieved.toFixed(1)} / {att.maxScore.toFixed(1)}
                                </span>
                              </td>
                              <td className="p-2.5 text-center">
                                {att.isCorrect ? (
                                  <span className="tactile-tag bg-brand-green text-white text-[10px] font-black">
                                    CORRECT
                                  </span>
                                ) : (
                                  <span className="tactile-tag bg-brand-coral text-white text-[10px] font-black">
                                    INCORRECT
                                  </span>
                                )}
                              </td>
                              <td className="p-2.5 text-right">
                                <button
                                  type="button"
                                  onClick={() => {
                                    const found = questions.find((q) => q.id === att.questionId);
                                    if (found) {
                                      setSelectedQuestion(found);
                                      setSubmissionResult(null);
                                      setAnswerInput(typeof att.submittedAnswer === "object" ? JSON.stringify(att.submittedAnswer) : String(att.submittedAnswer));
                                    } else if (att.objectiveId && att.objectiveId !== selectedObjectiveId) {
                                      setSelectedObjectiveId(att.objectiveId);
                                    }
                                  }}
                                  className="tactile-btn-white text-[10px] py-1 px-2 font-bold hover:!bg-brand-yellow"
                                >
                                  Inspect Explanation
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Main Practice & Evaluation 2-Column Grid */}
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
                          const rec = attemptHistory[q.id];
                          setAnswerInput(rec ? (typeof rec.submittedAnswer === "object" ? JSON.stringify(rec.submittedAnswer) : String(rec.submittedAnswer)) : "");
                          setNextAdaptiveRecommendation(null);
                        }
                      }}
                      className="tactile-select text-xs font-medium"
                    >
                      {questions.length === 0 ? (
                        <option value="">No questions found for this objective</option>
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
                              {statusTag}{q.title} ({q.question_type}) &bull; {q.versions[0]?.difficulty || "standard"}
                            </option>
                          );
                        })
                      )}
                    </select>
                  </div>
                </div>

                {/* Question Display Card */}
                {selectedQuestion && currentVersion ? (
                  <div className="tactile-card p-6 flex flex-col gap-5">
                    {/* Completion Status Alert with Awarded Marks */}
                    {isCurrentQuestionCompleted && (
                      <div className={`p-3 border-2 rounded-friendly-sm flex items-center justify-between text-xs font-bold animate-fade-in ${
                        isCorrect
                          ? "bg-brand-green/15 border-brand-green text-ink"
                          : "bg-brand-coral/15 border-brand-coral text-ink"
                      }`}>
                        <div className="flex items-center gap-2">
                          {isCorrect ? (
                            <CheckCircle2 className="w-4 h-4 text-brand-green shrink-0" />
                          ) : (
                            <XCircle className="w-4 h-4 text-brand-coral shrink-0" />
                          )}
                          <span>
                            {isCorrect
                              ? `Correct! Full Marks Awarded (+${scoreAchieved.toFixed(1)} / ${maxScore.toFixed(1)} Pts). Submit locked.`
                              : `Attempt Evaluated: 0.0 / ${maxScore.toFixed(1)} Marks. Submit locked.`}
                          </span>
                        </div>
                        <span className={`tactile-tag text-[10px] uppercase font-black ${
                          isCorrect ? "bg-brand-green text-white" : "bg-brand-coral text-white"
                        }`}>
                          {isCorrect ? "SOLVED ✓" : "ATTEMPTED"}
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
                          <span className="tactile-tag bg-surface text-ink text-[10px] font-bold">
                            Value: {currentVersion.max_score} Mark{currentVersion.max_score === 1 ? "" : "s"}
                          </span>
                          <span className="tactile-tag bg-brand-cyan/20 text-brand-cyan text-[10px]">
                            Grader: Pure Deterministic Logic
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
                          <div className={`flex items-center gap-2 px-4 py-2 border-2 rounded-friendly-sm text-xs font-black ${
                            isCorrect
                              ? "bg-brand-green/20 border-brand-green text-brand-green"
                              : "bg-brand-coral/20 border-brand-coral text-brand-coral"
                          }`}>
                            {isCorrect ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                            <span>{isCorrect ? "Solved (+1.0 Pts)" : "Evaluated (0.0 Pts)"}</span>
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
                  <span>Assessment &amp; Explanation</span>
                </h3>

                {isQuestionAnswered ? (
                  <div className="tactile-card p-6 flex flex-col gap-4 animate-fade-in">
                    {/* Result Status Banner */}
                    {isCorrect ? (
                      <div className="p-4 bg-brand-green/15 border-2 border-brand-green rounded-friendly-sm flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-5 h-5 text-brand-green shrink-0" />
                            <span className="font-black text-sm text-ink">
                              CORRECT ANSWER &bull; FULL MARKS AWARDED
                            </span>
                          </div>
                          <span className="tactile-tag bg-brand-green text-white text-xs font-black">
                            +{scoreAchieved.toFixed(1)} / {maxScore.toFixed(1)} MARKS
                          </span>
                        </div>
                        <p className="text-xs text-ink font-medium leading-relaxed">
                          Great job! Your answer matches the authoritative course answer key and passes all deterministic verification checks.
                        </p>
                      </div>
                    ) : (
                      <div className="p-4 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <XCircle className="w-5 h-5 text-brand-coral shrink-0" />
                            <span className="font-black text-sm text-ink">
                              INCORRECT ANSWER &bull; GAP IDENTIFIED
                            </span>
                          </div>
                          <span className="tactile-tag bg-brand-coral text-white text-xs font-black">
                            {scoreAchieved.toFixed(1)} / {maxScore.toFixed(1)} MARKS
                          </span>
                        </div>
                        <p className="text-xs text-ink font-medium leading-relaxed">
                          Your answer did not match the required derivation. Review the formal step-by-step solution below to master the concept.
                        </p>
                      </div>
                    )}

                    {/* Score & Evaluation Details */}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-3 bg-surface rounded-friendly-sm border-2 border-ink">
                        <span className="text-[10px] text-ink-muted font-black block uppercase">
                          Your Submitted Answer:
                        </span>
                        <span className="font-mono font-bold text-ink mt-0.5 block break-all">
                          {submittedAnswerVal || "None"}
                        </span>
                      </div>
                      <div className="p-3 bg-surface rounded-friendly-sm border-2 border-ink">
                        <span className="text-[10px] text-ink-muted font-black block uppercase">
                          Awarded Marks:
                        </span>
                        <span className={`font-black text-base mt-0.5 block ${isCorrect ? "text-brand-green" : "text-brand-coral"}`}>
                          {scoreAchieved.toFixed(1)} / {maxScore.toFixed(1)} Pts
                        </span>
                      </div>
                    </div>

                    {/* Deterministic Evaluation Steps (Grader Proof) */}
                    {evaluationSteps.length > 0 && (
                      <div className="flex flex-col gap-1.5 p-3 bg-surface border border-ink/20 rounded-friendly-sm">
                        <span className="text-[11px] font-black text-ink uppercase tracking-wider flex items-center gap-1.5">
                          <FileCheck2 className="w-3.5 h-3.5 text-brand-cyan" />
                          <span>Deterministic Evaluator Verification:</span>
                        </span>
                        <ul className="text-xs text-ink flex flex-col gap-1 mt-1">
                          {evaluationSteps.map((step, idx) => (
                            <li key={idx} className="flex items-start gap-1.5 font-medium">
                              <Check className="w-3.5 h-3.5 text-brand-green shrink-0 mt-0.5" />
                              <span>{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Deductions if any */}
                    {deductions.length > 0 && (
                      <div className="flex flex-col gap-1.5 p-3 bg-brand-coral/10 border border-brand-coral/30 rounded-friendly-sm">
                        <span className="text-[11px] font-black text-brand-coral uppercase tracking-wider flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-brand-coral" />
                          <span>Diagnosed Misconceptions &amp; Deductions:</span>
                        </span>
                        <ul className="text-xs text-ink flex flex-col gap-1 mt-1">
                          {deductions.map((d, idx) => (
                            <li key={idx} className="flex items-start gap-1.5 font-medium">
                              <X className="w-3.5 h-3.5 text-brand-coral shrink-0 mt-0.5" />
                              <span>
                                {d.reason}
                                {d.attributes ? `: [${(d.attributes as string[]).join(", ")}]` : ""}
                                {d.keys ? `: [${(d.keys as string[]).join(", ")}]` : ""}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Step-by-Step Mathematical Explanation & Solution */}
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-ink uppercase tracking-wider flex items-center gap-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-brand-yellow" />
                          <span>{isCorrect ? "Formal Proof & Step-by-Step Explanation:" : "Authoritative Solution & Explanation:"}</span>
                        </span>
                        {isCorrect && (
                          <span className="tactile-tag bg-brand-green/20 text-brand-green text-[10px] font-bold">
                            VERIFIED CORRECT
                          </span>
                        )}
                      </div>
                      <div className={`p-4 rounded-friendly-sm border-2 text-xs text-ink leading-relaxed font-medium whitespace-pre-wrap ${
                        isCorrect
                          ? "bg-brand-green/10 border-brand-green/40 text-ink shadow-hard-sm"
                          : "bg-brand-yellow/20 border-brand-yellow text-ink shadow-hard-sm"
                      }`}>
                        {explanationText}
                      </div>
                    </div>

                    {/* Expected Canonical Answer Key if present */}
                    {expectedKey && (
                      <div className="flex items-center justify-between p-2.5 bg-surface rounded border border-ink/20 text-xs">
                        <span className="font-bold text-ink-muted">Authoritative Answer Key:</span>
                        <span className="font-mono font-black text-ink">{expectedKey}</span>
                      </div>
                    )}

                    {/* Underlying Objective & Reference */}
                    <div className="flex flex-col gap-1.5 pt-2 border-t border-ink/10 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-ink">Underlying Learning Objective:</span>
                        <span className="tactile-tag bg-surface text-ink text-[10px]">
                          {activeObj?.code || "LO_EVAL"}
                        </span>
                      </div>
                      <div className="text-xs text-ink-muted font-medium">
                        {activeObj ? (
                          <>
                            <span className="font-bold text-ink">{activeObj.title}</span> &mdash; {activeObj.description}
                          </>
                        ) : (
                          "Relational functional dependencies and normal forms."
                        )}
                      </div>
                    </div>

                    {/* Source Citation */}
                    <div className="flex items-center gap-2 pt-2 border-t border-ink/10 text-xs">
                      <span className="font-bold text-ink">Grounded Citation:</span>
                      <span className="tactile-tag bg-surface text-ink text-[10px] font-mono">
                        {referenceCitation || "[Lecture: dbms_functional_dependencies.md, Page 1]"}
                      </span>
                    </div>

                    {/* Adaptive Next Question Action in Assessment Result */}
                    {nextAdaptiveRecommendation && (
                      <div className="p-3.5 bg-brand-yellow/20 border-2 border-ink rounded-friendly-sm flex flex-col gap-2 mt-2 shadow-hard-sm animate-fade-in">
                        <div className="flex items-center justify-between">
                          <span className={`tactile-tag text-[10px] font-black ${nextAdaptiveRecommendation.badgeColor}`}>
                            {nextAdaptiveRecommendation.badge}
                          </span>
                          <span className="text-[10px] font-mono font-bold text-ink-muted uppercase">Adaptive Progression</span>
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
                  <div className="tactile-card p-8 text-center text-ink-muted flex flex-col items-center gap-3">
                    <Play className="w-8 h-8 text-ink-faint" />
                    <p className="font-bold text-xs text-ink leading-relaxed">
                      Submit an answer to view the complete assessment breakdown, awarded marks, step-by-step formal explanation, and concept citation.
                    </p>
                    <p className="text-[11px] text-ink-muted">
                      Both correct and incorrect answers will display full proofs, score calculations, and lecture references.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })()}

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
