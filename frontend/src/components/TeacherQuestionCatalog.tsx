import React, { useState, useEffect } from "react";
import {
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  FileCheck2,
  HelpCircle,
  Layers,
  Lock,
  Plus,
  Search,
  Shield,
  Tag,
} from "lucide-react";
import {
  CourseResponse,
  LearningObjectiveResponse,
  QuestionResponse,
  QuestionVersionResponse,
  ScheduledAssessmentResponse,
  TopicResponse,
} from "../types";
import { recallApi } from "../lib/api-client";

function getActiveVersion(q: QuestionResponse | null): QuestionVersionResponse | undefined {
  if (!q || !q.versions || q.versions.length === 0) return undefined;
  return q.versions[q.versions.length - 1];
}

interface TeacherQuestionCatalogProps {
  course: CourseResponse | null;
  topics: TopicResponse[];
}

export function TeacherQuestionCatalog({
  course,
  topics,
}: TeacherQuestionCatalogProps) {
  const [selectedTopicId, setSelectedTopicId] = useState<string>("");
  const [selectedObjectiveId, setSelectedObjectiveId] = useState<string>("");
  const [questions, setQuestions] = useState<QuestionResponse[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // Scheduled assessments state for instructor
  const [scheduledAssessments, setScheduledAssessments] = useState<ScheduledAssessmentResponse[]>([]);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [newQuizTitle, setNewQuizTitle] = useState("");
  const [newQuizDesc, setNewQuizDesc] = useState("");
  const [newQuizDate, setNewQuizDate] = useState("");
  const [newQuizDuration, setNewQuizDuration] = useState(45);
  const [isSubmittingSchedule, setIsSubmittingSchedule] = useState(false);

  useEffect(() => {
    if (course?.id) {
      recallApi.listCourseAssessments(course.id).then(setScheduledAssessments).catch(() => {});
    }
  }, [course?.id]);

  const handleScheduleQuiz = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!course?.id || !newQuizTitle.trim()) return;
    setIsSubmittingSchedule(true);
    try {
      const scheduledAtIso = newQuizDate
        ? new Date(newQuizDate).toISOString()
        : new Date(Date.now() + 86400000).toISOString();
      const created = await recallApi.scheduleAssessment(course.id, {
        title: newQuizTitle.trim(),
        description: newQuizDesc.trim(),
        scheduled_at: scheduledAtIso,
        duration_minutes: Number(newQuizDuration) || 45,
        target_objective_id: selectedObjectiveId || null,
      });
      setScheduledAssessments((prev) => [...prev, created]);
      setNewQuizTitle("");
      setNewQuizDesc("");
      setShowScheduleForm(false);
      alert(`Quiz successfully scheduled! Enrolled students have been notified via in-app alert.`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to schedule assessment");
    } finally {
      setIsSubmittingSchedule(false);
    }
  };

  // Initialize selected topic and objective
  useEffect(() => {
    if (topics.length > 0 && !selectedTopicId) {
      setSelectedTopicId(topics[0].id);
      if (topics[0].objectives && topics[0].objectives.length > 0) {
        setSelectedObjectiveId(topics[0].objectives[0].id);
      }
    }
  }, [topics, selectedTopicId]);

  // When objective changes, fetch verified questions
  useEffect(() => {
    if (!selectedObjectiveId) {
      setQuestions([]);
      setSelectedQuestion(null);
      return;
    }
    const fetchQuestions = async () => {
      setLoading(true);
      try {
        const qList = await recallApi.listQuestionsForObjective(selectedObjectiveId);
        setQuestions(qList);
        setSelectedQuestion(qList.length > 0 ? qList[0] : null);
      } catch {
        setQuestions([]);
        setSelectedQuestion(null);
      } finally {
        setLoading(false);
      }
    };
    fetchQuestions();
  }, [selectedObjectiveId]);

  const activeTopic = topics.find((t) => t.id === selectedTopicId);
  const allObjectives: LearningObjectiveResponse[] = topics.flatMap(
    (t) => t.objectives || []
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="tactile-card p-5 bg-surface flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-coral text-white text-[10px] font-black">
              INSTRUCTOR CATALOG INSPECTOR
            </span>
            <span className="text-xs font-bold text-ink-muted">
              Course: {course?.code || "CS340"}
            </span>
          </div>
          <h2 className="text-xl font-black text-ink">
            Verified Question Bank &amp; Rubric Governance
          </h2>
          <p className="text-xs text-ink-muted font-medium mt-0.5">
            Inspect formal answer keys, deterministic Armstrong evaluation rubrics, difficulty levels, and provenance credentials across all DAG objectives.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowScheduleForm(!showScheduleForm)}
            className="tactile-btn-yellow text-xs py-1.5 px-3 flex items-center gap-1.5 font-bold"
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>{showScheduleForm ? "Close Scheduler" : "+ Schedule Course Quiz"}</span>
          </button>
          <span className="tactile-tag bg-brand-green/20 text-ink text-xs font-bold">
            {questions.length} Verified Qs
          </span>
        </div>
      </div>

      {/* Teacher Quiz Scheduler Form Panel */}
      {showScheduleForm && (
        <form
          onSubmit={handleScheduleQuiz}
          className="tactile-card p-5 bg-white border-2 border-ink shadow-hard flex flex-col gap-4"
        >
          <div className="border-b border-ink/10 pb-2">
            <h3 className="text-sm font-black text-ink flex items-center gap-2">
              <Calendar className="w-4 h-4 text-brand-coral" />
              <span>Schedule New Quiz / Assessment &bull; Auto-Alerts Enrolled Cohort</span>
            </h3>
            <p className="text-[11px] text-ink-muted mt-0.5">
              Scheduled quizzes are persisted in the course calendar and immediately trigger in-app notifications for enrolled students.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink">Quiz / Exam Title *</label>
              <input
                type="text"
                required
                value={newQuizTitle}
                onChange={(e) => setNewQuizTitle(e.target.value)}
                placeholder="e.g. Midterm Test: Normalization & Keys"
                className="tactile-input text-xs"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink">Scheduled Date &amp; Time *</label>
              <input
                type="datetime-local"
                value={newQuizDate}
                onChange={(e) => setNewQuizDate(e.target.value)}
                className="tactile-input text-xs"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink">Duration (Minutes)</label>
              <input
                type="number"
                min="5"
                max="180"
                value={newQuizDuration}
                onChange={(e) => setNewQuizDuration(Number(e.target.value))}
                className="tactile-input text-xs"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink">Description / Scope Notes</label>
              <input
                type="text"
                value={newQuizDesc}
                onChange={(e) => setNewQuizDesc(e.target.value)}
                placeholder="e.g. Covers 1NF through BCNF and attribute closures."
                className="tactile-input text-xs"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-ink/10">
            <button
              type="button"
              onClick={() => setShowScheduleForm(false)}
              className="tactile-btn-white text-xs py-1.5 px-3 font-bold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingSchedule || !newQuizTitle.trim()}
              className="tactile-btn-coral text-xs py-1.5 px-4 font-black"
            >
              {isSubmittingSchedule ? "Scheduling & Alerting..." : "Publish Assessment & Alert Cohort"}
            </button>
          </div>
        </form>
      )}

      {/* Existing Scheduled Assessments List */}
      {scheduledAssessments.length > 0 && (
        <div className="tactile-card p-4 bg-surface-warm/40 border-2 border-ink flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black text-ink uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-brand-coral" />
              <span>Published Course Assessments ({scheduledAssessments.length})</span>
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {scheduledAssessments.map((a) => (
              <div
                key={a.id}
                className="p-3 bg-white border border-ink rounded text-xs flex flex-col gap-1 shadow-hard-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="font-black text-ink">{a.title}</span>
                  <span className="tactile-tag bg-brand-coral text-white text-[9px] uppercase font-bold">
                    {a.duration_minutes}m &bull; {a.status}
                  </span>
                </div>
                <div className="text-[11px] text-ink-muted">
                  {new Date(a.scheduled_at).toLocaleString()}
                </div>
                {a.description && <div className="text-[11px] text-ink-muted">{a.description}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selectors Bar */}
      <div className="tactile-card p-4 grid grid-cols-1 md:grid-cols-2 gap-4 bg-surface">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-ink flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-brand-cyan" />
            <span>Curriculum Topic Cluster:</span>
          </label>
          <select
            value={selectedTopicId}
            onChange={(e) => {
              const topId = e.target.value;
              setSelectedTopicId(topId);
              const top = topics.find((t) => t.id === topId);
              if (top && top.objectives && top.objectives.length > 0) {
                setSelectedObjectiveId(top.objectives[0].id);
              } else {
                setSelectedObjectiveId("");
              }
            }}
            className="tactile-select text-xs font-bold"
          >
            {topics.map((t) => (
              <option key={t.id} value={t.id}>
                {t.code} &mdash; {t.title}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-ink flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-brand-yellow" />
            <span>Learning Objective:</span>
          </label>
          <select
            value={selectedObjectiveId}
            onChange={(e) => setSelectedObjectiveId(e.target.value)}
            className="tactile-select text-xs font-bold"
          >
            {(activeTopic?.objectives || allObjectives).map((obj) => (
              <option key={obj.id} value={obj.id}>
                {obj.code} &mdash; {obj.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Content: Left Column Question List, Right Column Question Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Questions in Objective */}
        <div className="lg:col-span-5 flex flex-col gap-3">
          <div className="flex items-center justify-between pb-1 border-b border-ink/10">
            <span className="text-xs font-black uppercase text-ink">
              Verified Questions ({questions.length})
            </span>
          </div>

          {loading ? (
            <div className="p-8 text-center text-xs font-bold text-ink-muted">
              Loading verified questions...
            </div>
          ) : questions.length === 0 ? (
            <div className="p-8 text-center text-xs font-bold text-ink-muted bg-surface rounded-friendly border-2 border-dashed border-ink/20">
              No questions found for this objective.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {questions.map((q) => {
                const isSelected = selectedQuestion?.id === q.id;
                const ver = getActiveVersion(q);
                return (
                  <div
                    key={q.id}
                    onClick={() => setSelectedQuestion(q)}
                    className={`p-3 rounded-friendly-sm border-2 border-ink cursor-pointer transition-all ${
                      isSelected
                        ? "bg-brand-yellow text-ink shadow-hard-sm"
                        : "bg-surface hover:bg-surface-warm"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-mono text-[10px] font-black uppercase bg-ink/10 px-1.5 py-0.5 rounded">
                        {q.question_type}
                      </span>
                      <span className="text-[10px] font-bold text-ink-muted">
                        {ver?.difficulty || "standard"}
                      </span>
                    </div>
                    <div className="text-xs font-bold text-ink line-clamp-2">
                      {q.title}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Detailed Question Inspector */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          {(() => {
            const activeVer = getActiveVersion(selectedQuestion);
            if (!selectedQuestion || !activeVer) {
              return (
                <div className="tactile-card p-12 text-center text-ink-muted">
                  <HelpCircle className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
                  <p className="font-bold text-sm">Select a question to inspect details.</p>
                </div>
              );
            }
            return (
              <div className="tactile-card p-6 flex flex-col gap-5 bg-surface">
                {/* Question Header & Provenance */}
                <div className="flex flex-col gap-2 pb-4 border-b border-ink/10">
                  <div className="flex items-center justify-between">
                    <span className="tactile-tag bg-brand-green text-ink text-[10px] font-black">
                      VERIFIED QUESTION
                    </span>
                    <span className="font-mono text-[10px] text-ink-muted">
                      ID: {selectedQuestion.id.substring(0, 8)}...
                    </span>
                  </div>
                  <h3 className="text-lg font-black text-ink">
                    {selectedQuestion.title}
                  </h3>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-bold text-ink-muted">
                    <span>Type: <strong className="text-ink uppercase">{selectedQuestion.question_type}</strong></span>
                    <span>&bull;</span>
                    <span>Difficulty: <strong className="text-ink uppercase">{activeVer.difficulty}</strong></span>
                    <span>&bull;</span>
                    <span>Max Score: <strong className="text-ink">{activeVer.max_score} pts</strong></span>
                  </div>
                </div>

                {/* Question Statement */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-ink">Question Statement:</label>
                  <div className="p-4 bg-surface-warm/40 border-2 border-ink rounded-friendly-sm text-xs font-mono whitespace-pre-wrap leading-relaxed">
                    {activeVer.prompt}
                  </div>
                </div>

                {/* Options if MCQ/Multi-select */}
                {activeVer.options && activeVer.options.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-ink">Options:</label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {(activeVer.options as Array<{ id?: string; text?: string }>).map((opt) => (
                        <div
                          key={String(opt.id || "")}
                          className="p-2.5 bg-surface rounded border border-ink/20 text-xs flex items-center gap-2"
                        >
                          <span className="font-mono font-black bg-ink/10 px-1.5 py-0.5 rounded text-[11px]">
                            {String(opt.id || "")}
                          </span>
                          <span className="font-medium text-ink">{String(opt.text || "")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Verified Answer Key */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-ink flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-brand-green" />
                    <span>Verified Answer Key:</span>
                  </label>
                  <div className="p-3 bg-brand-green/10 border-2 border-brand-green rounded-friendly-sm text-xs font-mono font-bold text-ink">
                    {JSON.stringify(activeVer.answer_key, null, 2)}
                  </div>
                </div>

                {/* Deterministic Grading Rubric */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-ink flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-brand-cyan" />
                    <span>Deterministic Grader Rubric:</span>
                  </label>
                  <div className="p-3 bg-surface-warm/30 border border-ink/20 rounded-friendly-sm text-xs font-mono">
                    {JSON.stringify(activeVer.rubric, null, 2)}
                  </div>
                </div>

                {/* Explanation & Authoritative Provenance */}
                <div className="p-3 bg-surface rounded border border-ink/20 flex flex-col gap-2">
                  <span className="text-[11px] font-bold text-ink">Pedagogical Explanation:</span>
                  <p className="text-xs text-ink-muted leading-relaxed">
                    {activeVer.explanation || "No explanation recorded."}
                  </p>
                  <div className="pt-2 border-t border-ink/10 flex items-center justify-between text-[10px] font-mono text-ink-muted">
                    <span>Verified by: {activeVer.verified_by || "Course Professor"}</span>
                    <span className="truncate max-w-[200px]" title={activeVer.provenance_hash || ""}>
                      Provenance: {activeVer.provenance_hash?.substring(0, 16)}...
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
