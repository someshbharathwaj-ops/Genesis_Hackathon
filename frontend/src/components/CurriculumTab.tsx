"use client";

import React, { useState } from "react";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Code2,
  FileQuestion,
  Layers,
  Sparkles,
} from "lucide-react";
import { CourseResponse, LearningObjectiveResponse, QuestionResponse, TopicResponse } from "../types";
import { recallApi } from "../lib/api-client";

interface CurriculumTabProps {
  course: CourseResponse | null;
  topics: TopicResponse[];
  onSelectObjectiveForPractice?: (objective: LearningObjectiveResponse) => void;
}

export function CurriculumTab({
  course,
  topics,
  onSelectObjectiveForPractice,
}: CurriculumTabProps) {
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>(
    topics.length > 0 ? topics[0].id : null
  );
  const [selectedTopicFilter, setSelectedTopicFilter] = useState<string>("ALL");
  const [selectedObjective, setSelectedObjective] = useState<LearningObjectiveResponse | null>(null);
  const [objectiveQuestions, setObjectiveQuestions] = useState<QuestionResponse[]>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);

  const displayedTopics =
    selectedTopicFilter === "ALL"
      ? topics
      : topics.filter((t) => t.id === selectedTopicFilter);

  const handleObjectiveClick = async (objective: LearningObjectiveResponse) => {
    setSelectedObjective(objective);
    setLoadingQuestions(true);
    try {
      const qs = await recallApi.listQuestionsForObjective(objective.id);
      setObjectiveQuestions(qs);
    } catch {
      setObjectiveQuestions([]);
    } finally {
      setLoadingQuestions(false);
    }
  };

  if (!course) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <BookOpen className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">No course selected. Please select or seed a course.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Course Overview Banner */}
      <section className="tactile-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-cyan text-ink">{course.code}</span>
            <span className="text-xs font-bold text-ink-muted">Authoritative Curriculum</span>
          </div>
          <h2 className="text-2xl font-black text-ink">{course.title}</h2>
          <p className="text-sm text-ink-muted mt-1 max-w-2xl font-medium">
            {course.description || "Course curriculum and versioned objective hierarchy."}
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="bg-surface-warm border-2 border-ink p-3 rounded-friendly-sm shadow-hard-sm text-center">
            <div className="text-xl font-black text-ink">{topics.length}</div>
            <div className="text-ink-muted font-bold">Topics</div>
          </div>
          <div className="bg-surface-warm border-2 border-ink p-3 rounded-friendly-sm shadow-hard-sm text-center">
            <div className="text-xl font-black text-ink">
              {topics.reduce((acc, t) => acc + t.objectives.length, 0)}
            </div>
            <div className="text-ink-muted font-bold">Objectives</div>
          </div>
        </div>
      </section>

      {/* Topic / DAG Cluster Filter Bar */}
      {topics.length > 1 && (
        <div className="flex flex-col gap-2">
          <div className="text-xs font-bold text-ink-muted uppercase tracking-wider flex items-center justify-between">
            <span>Select Curriculum DAG to Explore:</span>
            <span className="font-mono text-[11px] font-black text-brand-cyan">
              {selectedTopicFilter === "ALL"
                ? `Showing All ${topics.length} DAG Clusters`
                : topics.find((t) => t.id === selectedTopicFilter)?.title}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSelectedTopicFilter("ALL")}
              className={`tactile-btn-white text-xs py-1.5 px-3 font-bold ${
                selectedTopicFilter === "ALL"
                  ? "!bg-brand-yellow !shadow-hard-sm"
                  : ""
              }`}
            >
              <span>🌐 All DAG Clusters ({topics.length})</span>
            </button>
            {topics.map((t) => (
              <button
                key={t.id}
                onClick={() => {
                  setSelectedTopicFilter(t.id);
                  setExpandedTopicId(t.id);
                }}
                className={`tactile-btn-white text-xs py-1.5 px-3 font-bold ${
                  selectedTopicFilter === t.id
                    ? "!bg-brand-cyan !text-ink !shadow-hard-sm"
                    : ""
                }`}
              >
                <span>📚 DAG #{t.order_index}: {t.code}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Curriculum DAG & Objectives Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Topics & Objectives Hierarchy */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <h3 className="text-lg font-black text-ink flex items-center gap-2">
            <Layers className="w-5 h-5 text-brand-yellow" />
            <span>Topics & Prerequisites DAG</span>
          </h3>

          {displayedTopics.length === 0 ? (
            <div className="tactile-card p-6 text-center text-ink-muted text-sm">
              No topics found for {course?.code || "this course"}. Click &quot;Seed {course?.code || "Course"}&quot; in the header to initialize curriculum.
            </div>
          ) : (
            displayedTopics.map((topic) => {
              const isExpanded = expandedTopicId === topic.id;
              return (
                <div key={topic.id} className="tactile-card overflow-hidden">
                  <button
                    onClick={() => setExpandedTopicId(isExpanded ? null : topic.id)}
                    className="w-full p-4 flex items-center justify-between text-left hover:bg-surface-warm/40 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-friendly-sm bg-brand-yellow border-2 border-ink flex items-center justify-center font-bold text-xs">
                        {topic.order_index}
                      </div>
                      <div>
                        <div className="font-black text-sm text-ink">{topic.title}</div>
                        <div className="text-xs text-ink-muted font-medium">{topic.code}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="tactile-tag bg-surface text-ink text-[10px]">
                        {topic.objectives.length} Objectives
                      </span>
                      {topic.objectives.length > 0 && onSelectObjectiveForPractice && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectObjectiveForPractice(topic.objectives[0]);
                          }}
                          className="tactile-btn-yellow text-[10px] py-1 px-2 font-bold flex items-center gap-1 shadow-hard-sm"
                          title="Practice questions attached to this topic DAG"
                        >
                          <Sparkles className="w-3 h-3 text-ink" />
                          <span>Practice DAG</span>
                        </button>
                      )}
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-ink" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-ink" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="p-4 border-t-2 border-ink/10 flex flex-col gap-3 bg-surface-warm/20">
                      {topic.objectives.map((obj) => {
                        const isSelected = selectedObjective?.id === obj.id;
                        return (
                          <div
                            key={obj.id}
                            onClick={() => handleObjectiveClick(obj)}
                            className={`p-3 border-2 border-ink rounded-friendly-sm cursor-pointer transition-all ${
                              isSelected
                                ? "bg-brand-yellow shadow-hard-sm"
                                : "bg-surface hover:bg-surface-warm shadow-hard-pressed"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs font-bold text-ink">
                                {obj.code}
                              </span>
                              <span className="text-[11px] font-bold text-ink-muted">
                                Step #{obj.order_index}
                              </span>
                            </div>
                            <div className="font-bold text-sm text-ink mt-1">{obj.title}</div>
                            <p className="text-xs text-ink-muted mt-1 font-medium">
                              {obj.description}
                            </p>

                            {/* Prerequisites DAG Tags */}
                            {obj.prerequisite_objective_ids &&
                              obj.prerequisite_objective_ids.length > 0 && (
                                <div className="mt-2 flex flex-wrap items-center gap-1.5 pt-2 border-t border-ink/10">
                                  <span className="text-[10px] font-bold text-ink-muted">
                                    Prerequisites:
                                  </span>
                                  {obj.prerequisite_objective_ids.map((preId) => {
                                    // Try matching code from other objectives
                                    const preObj = topic.objectives.find(
                                      (o) => o.id === preId || o.code === preId
                                    );
                                    return (
                                      <span
                                        key={preId}
                                        className="tactile-tag bg-surface-muted text-ink text-[9px] py-0 px-1.5"
                                      >
                                        <ArrowRight className="w-2.5 h-2.5 text-brand-coral inline" />
                                        <span>{preObj ? preObj.code : preId}</span>
                                      </span>
                                    );
                                  })}
                                </div>
                              )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Right: Selected Objective Questions & Catalog */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <h3 className="text-lg font-black text-ink flex items-center gap-2">
            <FileQuestion className="w-5 h-5 text-brand-coral" />
            <span>Verified Question Bank</span>
          </h3>

          {selectedObjective ? (
            <div className="tactile-card p-5 flex flex-col gap-4">
              <div className="pb-3 border-b-2 border-ink/10">
                <div className="flex items-center justify-between">
                  <span className="tactile-tag bg-brand-yellow text-ink text-xs">
                    {selectedObjective.code}
                  </span>
                  {onSelectObjectiveForPractice && (
                    <button
                      onClick={() => onSelectObjectiveForPractice(selectedObjective)}
                      className="tactile-btn-yellow text-xs py-1 px-3"
                    >
                      <Sparkles className="w-3 h-3" />
                      <span>Practice Objective</span>
                    </button>
                  )}
                </div>
                <div className="font-black text-base text-ink mt-2">
                  {selectedObjective.title}
                </div>
                <p className="text-xs text-ink-muted mt-1 font-medium">
                  {selectedObjective.description}
                </p>
              </div>

              {loadingQuestions ? (
                <div className="p-6 text-center text-xs font-bold text-ink-muted">
                  Loading verified questions...
                </div>
              ) : objectiveQuestions.length === 0 ? (
                <div className="p-6 text-center text-xs text-ink-muted font-medium">
                  No verified questions currently attached to this objective.
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="text-xs font-bold text-ink-muted">
                    {objectiveQuestions.length} Verified Question(s) in Catalog:
                  </div>
                  {objectiveQuestions.map((q) => {
                    const version = q.versions[0];
                    return (
                      <div
                        key={q.id}
                        className="p-3 bg-surface-warm/40 border-2 border-ink rounded-friendly-sm flex flex-col gap-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-black text-ink">{q.title}</span>
                          <span className="tactile-tag bg-brand-green text-ink text-[10px] py-0 px-1.5 uppercase">
                            {version?.difficulty || "verified"}
                          </span>
                        </div>
                        {version && (
                          <>
                            <p className="text-xs text-ink-muted font-medium italic">
                              &quot;{version.prompt}&quot;
                            </p>
                            <div className="text-[10px] font-mono text-ink-muted pt-1 border-t border-ink/10 flex justify-between">
                              <span>Max Points: {version.max_score}</span>
                              <span>Verified by: {version.verified_by || "Authoritative Key"}</span>
                            </div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="tactile-card p-8 text-center text-ink-muted flex flex-col items-center justify-center gap-2 min-h-[240px]">
              <Code2 className="w-8 h-8 text-ink-faint" />
              <div className="font-bold text-sm">Select a Learning Objective</div>
              <p className="text-xs max-w-xs font-medium">
                Click any objective on the left to inspect its verified assessment questions and
                rubric parameters.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
