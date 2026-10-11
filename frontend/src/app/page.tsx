"use client";

import React, { useEffect, useState } from "react";
import {
  BookOpen,
  Brain,
  Calendar,
  Compass,
  FileCheck2,
  FileText,
  GraduationCap,
  HelpCircle,
  Layers,
  Lock,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import {
  clearStoredToken,
  getStoredToken,
  recallApi,
  setStoredToken,
} from "../lib/api-client";
import {
  CourseResponse,
  HealthResponse,
  LearningObjectiveResponse,
  ReadinessResponse,
  TopicResponse,
  UserResponse,
} from "../types";
import { CurriculumTab } from "../components/CurriculumTab";
import { KnowledgeTab } from "../components/KnowledgeTab";
import { LoginView } from "../components/LoginView";
import { MasteryDiagnosisTab } from "../components/MasteryDiagnosisTab";
import { Navbar } from "../components/Navbar";
import { RevisorTab } from "../components/RevisorTab";
import { SchedulingTab } from "../components/SchedulingTab";
import { TutorTab } from "../components/TutorTab";
import { AdminAuditDashboard } from "../components/AdminAuditDashboard";

type MentorMode = "tutor" | "revisor";
type ActiveTab =
  | "tutor"
  | "revisor"
  | "curriculum"
  | "mastery"
  | "scheduling"
  | "teacher_knowledge"
  | "admin_audit";

export default function HomePage() {
  // Global Platform State
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [courses, setCourses] = useState<CourseResponse[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<CourseResponse | null>(null);
  const [topics, setTopics] = useState<TopicResponse[]>([]);

  // Navigation & Mode State
  const [mentorMode, setMentorMode] = useState<MentorMode>("tutor");
  const [activeTab, setActiveTab] = useState<ActiveTab>("tutor");
  const [isSeeding, setIsSeeding] = useState<boolean>(false);
  const [activeScoredAssessmentId, setActiveScoredAssessmentId] = useState<string | null>(null);
  const [targetObjectiveForPractice, setTargetObjectiveForPractice] =
    useState<LearningObjectiveResponse | null>(null);
  const [authInitialized, setAuthInitialized] = useState<boolean>(false);

  // Initialize Platform
  const initializePlatform = async () => {
    try {
      const [healthData, readyData] = await Promise.all([
        recallApi.getHealth().catch(() => null),
        recallApi.getReadiness().catch(() => null),
      ]);
      if (healthData) setHealth(healthData);
      if (readyData) setReadiness(readyData);

      // Check current token
      const token = getStoredToken();
      if (token) {
        try {
          const me = await recallApi.getMe();
          setCurrentUser(me.user);
        } catch {
          clearStoredToken();
          setCurrentUser(null);
        }
      }

      // Fetch Courses
      let courseList = await recallApi.listCourses().catch(() => []);
      if (courseList.length === 0) {
        try {
          await recallApi.seedDbmsCourse();
          courseList = await recallApi.listCourses();
        } catch {
          courseList = [];
        }
      }
      setCourses(courseList);

      if (courseList.length > 0) {
        const primary = courseList[0];
        setSelectedCourse(primary);
        const topList = await recallApi.getCourseTopics(primary.id).catch(() => []);
        setTopics(topList);
      }
    } catch (err) {
      console.error("Platform initialization error:", err);
    } finally {
      setAuthInitialized(true);
    }
  };

  useEffect(() => {
    initializePlatform();
  }, []);

  // Course Selection Handler
  const handleSelectCourse = async (course: CourseResponse) => {
    setSelectedCourse(course);
    try {
      const topList = await recallApi.getCourseTopics(course.id);
      setTopics(topList);
    } catch {
      setTopics([]);
    }
  };

  // Demo Login Handler
  const handleDemoLogin = async (role: "student" | "instructor" | "admin") => {
    try {
      const resp = await recallApi.demoLogin(role, selectedCourse?.code || "CS340");
      setStoredToken(resp.access_token);
      setCurrentUser(resp.user);
      if (resp.user.role === "admin") {
        setActiveTab("admin_audit");
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to switch demo identity.");
    }
  };

  // Logout Handler: Fully clears client session and redirects to LoginView
  const handleLogout = () => {
    clearStoredToken();
    setCurrentUser(null);
    setActiveTab("tutor");
    setMentorMode("tutor");
  };

  // Seed Dynamic Course Handler
  const handleSeedCourse = async (codeToSeed?: string) => {
    const targetCode = (codeToSeed || selectedCourse?.code || "CS340").trim();
    setIsSeeding(true);
    try {
      if (targetCode.toUpperCase() === "CS301" || targetCode.toUpperCase() === "OS") {
        await recallApi.seedOsCourse();
      } else if (targetCode.toUpperCase() === "CS340" || targetCode.toUpperCase() === "DBMS") {
        await recallApi.seedDbmsCourse();
      } else {
        await recallApi.seedCourse(targetCode);
      }
      const courseList = await recallApi.listCourses();
      setCourses(courseList);
      const updated =
        courseList.find((c) => c.code.toUpperCase() === targetCode.toUpperCase()) ||
        courseList[0];
      if (updated) {
        handleSelectCourse(updated);
      }
      alert(`Successfully seeded ${targetCode} curriculum, verified questions, and knowledge base!`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : `Failed to seed course ${targetCode}.`);
    } finally {
      setIsSeeding(false);
    }
  };

  // Seed / Create Brand New Course Handler
  const handleSeedNewCourse = async (payload: {
    code: string;
    title: string;
    description?: string;
  }) => {
    setIsSeeding(true);
    try {
      await recallApi.seedNewCourse(payload);
      const courseList = await recallApi.listCourses();
      setCourses(courseList);
      const matched =
        courseList.find((c) => c.code.toUpperCase() === payload.code.toUpperCase()) ||
        courseList[courseList.length - 1];
      if (matched) {
        handleSelectCourse(matched);
      }
      alert(`Successfully initialized and seeded ${payload.code}: ${payload.title}!`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : `Failed to seed new course ${payload.code}.`);
    } finally {
      setIsSeeding(false);
    }
  };

  // Mode Switching Handlers
  const handleSwitchMode = (mode: MentorMode) => {
    setMentorMode(mode);
    setActiveTab(mode);
  };

  const handleSwitchToRevisorWithObjective = (obj: LearningObjectiveResponse) => {
    setTargetObjectiveForPractice(obj);
    setMentorMode("revisor");
    setActiveTab("revisor");
  };

  // Render Gate: Loading check while verifying session
  if (!authInitialized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="font-bold text-sm text-ink animate-pulse">
          Loading Recall AI Mentor...
        </div>
      </div>
    );
  }

  // Render Gate: If unauthenticated, show clean institutional Sign-In screen
  if (!currentUser) {
    return (
      <LoginView
        onLoginSuccess={(user) => {
          setCurrentUser(user);
          setActiveTab("tutor");
          setMentorMode("tutor");
        }}
        selectedCourseCode={selectedCourse?.code || "CS340"}
        courses={courses}
        onSelectCourse={handleSelectCourse}
      />
    );
  }

  const isInstructor = currentUser?.role === "instructor";

  return (
    <div className="min-h-screen bg-background text-ink flex flex-col">
      {/* Top Navigation & Identity Bar */}
      <div className="max-w-7xl mx-auto w-full px-4 pt-6 md:pt-8">
        <Navbar
          currentUser={currentUser}
          courses={courses}
          selectedCourse={selectedCourse}
          onSelectCourse={handleSelectCourse}
          onLoginDemo={handleDemoLogin}
          onLogout={handleLogout}
          onSeedCourse={handleSeedCourse}
          onSeedNewCourse={handleSeedNewCourse}
          isSeeding={isSeeding}
          hasActiveScoredAssessment={!!activeScoredAssessmentId}
        />
      </div>

      {/* Main Content Router: Admin Console vs Student/Instructor Learning Platform */}
      {currentUser?.role === "admin" ? (
        <div className="max-w-7xl mx-auto w-full px-4 py-6 flex flex-col gap-6">
          <AdminAuditDashboard
            currentUser={currentUser}
            courses={courses}
            onRefreshCourses={initializePlatform}
          />
        </div>
      ) : (
        <div className="max-w-7xl mx-auto w-full px-4 py-6 flex flex-col gap-6">
          {/* ============================================================== */}
          {/* RECALL AI MENTOR WELCOME & DUAL-MODE SELECTION                 */}
          {/* ============================================================== */}
        <section className="tactile-card p-6 bg-surface flex flex-col gap-5">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-ink/10 pb-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="tactile-tag bg-brand-yellow text-ink text-xs font-black">
                  AI MENTOR PLATFORM
                </span>
                <span className="text-xs font-bold text-ink-muted">
                  Course: {selectedCourse?.code || "CS340"} &mdash; {selectedCourse?.title || "DBMS"}
                </span>
              </div>
              <h1 className="text-2xl font-black text-ink">
                Welcome, {currentUser?.full_name || "Student"}!
              </h1>
              <p className="text-xs text-ink-muted font-medium mt-0.5">
                Choose how you want to learn today. Seamlessly switch between conceptual teaching and practice while preserving course progress.
              </p>
            </div>

            {/* Current Active Mode Indicator */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-ink-muted">Current Mode:</span>
              <span
                className={`tactile-tag text-xs font-black uppercase ${
                  mentorMode === "tutor"
                    ? "bg-brand-yellow text-ink"
                    : "bg-brand-coral text-white"
                }`}
              >
                {mentorMode === "tutor" ? "Mode A: Tutor" : "Mode B: Revisor"}
              </span>
            </div>
          </div>

          {/* Two Large Differentiated Mode Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Card A: Tutor Mode */}
            <div
              onClick={() => handleSwitchMode("tutor")}
              className={`p-5 rounded-friendly border-2 border-ink cursor-pointer transition-all ${
                mentorMode === "tutor"
                  ? "bg-brand-yellow/20 border-brand-yellow shadow-hard"
                  : "bg-surface hover:bg-surface-warm"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-friendly-sm bg-brand-yellow border-2 border-ink flex items-center justify-center font-black text-ink shadow-hard-sm">
                    <MessageSquare className="w-5 h-5 text-ink" />
                  </div>
                  <div>
                    <span className="tactile-tag bg-brand-yellow text-ink text-[10px] font-black">
                      MODE A &bull; TEACH &amp; EXPLAIN
                    </span>
                    <h2 className="text-lg font-black text-ink mt-0.5">Grounded AI Tutor</h2>
                  </div>
                </div>
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                    mentorMode === "tutor"
                      ? "bg-brand-yellow text-ink border-ink font-black"
                      : "bg-surface text-ink-muted border-ink/20"
                  }`}
                >
                  {mentorMode === "tutor" ? "ACTIVE" : "SELECT"}
                </span>
              </div>
              <p className="text-xs text-ink-muted font-medium mt-3 leading-relaxed">
                Understand concepts from the ground up, ask follow-up questions, request analogies, and receive step-by-step explanations with exact citations to verified course materials.
              </p>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-ink/10 text-[11px] font-bold text-ink">
                <Sparkles className="w-3.5 h-3.5 text-brand-yellow" />
                <span>Zero Grading Authority &bull; Strict Abstention Policy</span>
              </div>
            </div>

            {/* Card B: Revisor Mode */}
            <div
              onClick={() => handleSwitchMode("revisor")}
              className={`p-5 rounded-friendly border-2 border-ink cursor-pointer transition-all ${
                mentorMode === "revisor"
                  ? "bg-brand-coral/15 border-brand-coral shadow-hard"
                  : "bg-surface hover:bg-surface-warm"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-friendly-sm bg-brand-coral border-2 border-ink flex items-center justify-center font-black text-white shadow-hard-sm">
                    <ShieldCheck className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <span className="tactile-tag bg-brand-coral text-white text-[10px] font-black">
                      MODE B &bull; PRACTISE &amp; TEST
                    </span>
                    <h2 className="text-lg font-black text-ink mt-0.5">Adaptive Revisor</h2>
                  </div>
                </div>
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                    mentorMode === "revisor"
                      ? "bg-brand-coral text-white border-ink font-black"
                      : "bg-surface text-ink-muted border-ink/20"
                  }`}
                >
                  {mentorMode === "revisor" ? "ACTIVE" : "SELECT"}
                </span>
              </div>
              <p className="text-xs text-ink-muted font-medium mt-3 leading-relaxed">
                Practise deterministic questions across all 5 DBMS objectives, take mock assessments, audit conceptual explanations against course notes, and follow personalized revision schedules.
              </p>
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-ink/10 text-[11px] font-bold text-ink">
                <Lock className="w-3.5 h-3.5 text-brand-coral" />
                <span>Deterministic Mathematical Grader &bull; Exam Lockout Protected</span>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================== */}
        {/* PERSISTENT VISUAL MODE BANNER                                  */}
        {/* ============================================================== */}
        <div
          className={`p-4 rounded-friendly-sm border-2 border-ink flex flex-wrap items-center justify-between gap-3 shadow-hard-sm ${
            mentorMode === "tutor"
              ? "bg-brand-yellow/15 border-brand-yellow"
              : "bg-brand-coral/15 border-brand-coral"
          }`}
        >
          <div className="flex items-center gap-3">
            <span
              className={`tactile-tag text-xs font-black ${
                mentorMode === "tutor"
                  ? "bg-brand-yellow text-ink"
                  : "bg-brand-coral text-white"
              }`}
            >
              {mentorMode === "tutor" ? "TUTOR MODE ENGAGED" : "REVISOR MODE ENGAGED"}
            </span>
            <span className="text-xs font-bold text-ink">
              {mentorMode === "tutor"
                ? "Syllabus Explainer active &bull; Course evidence bound &bull; Phi-3 Mini"
                : "Practice & Audit active &bull; Pure deterministic grader authority &bull; Prerequisite aware"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleSwitchMode(mentorMode === "tutor" ? "revisor" : "tutor")}
              className="tactile-btn-white text-xs py-1.5 px-3 font-bold"
            >
              <span>Switch to {mentorMode === "tutor" ? "Revisor Mode" : "Tutor Mode"}</span>
            </button>
          </div>
        </div>

        {/* Secondary Navigation Bar */}
        <nav className="flex flex-wrap items-center gap-2 pb-2 border-b-2 border-ink/10">
          <button
            onClick={() => {
              setActiveTab("tutor");
              setMentorMode("tutor");
            }}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "tutor" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-brand-yellow" />
            <span>AI Tutor</span>
          </button>

          <button
            onClick={() => {
              setActiveTab("revisor");
              setMentorMode("revisor");
            }}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "revisor" ? "!bg-brand-coral !text-white !shadow-hard-sm" : ""
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-brand-coral" />
            <span>Revisor (Practice &amp; Audit)</span>
          </button>

          <button
            onClick={() => setActiveTab("curriculum")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "curriculum" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Curriculum DAG</span>
          </button>

          <button
            onClick={() => setActiveTab("mastery")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "mastery" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <Brain className="w-3.5 h-3.5 text-brand-green" />
            <span>Mastery &amp; Diagnosis</span>
          </button>

          <button
            onClick={() => setActiveTab("scheduling")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "scheduling" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <Calendar className="w-3.5 h-3.5 text-brand-cyan" />
            <span>Revision Schedule (Rule 6)</span>
          </button>

          {/* Instructor-Only Classroom Materials Tab */}
          {isInstructor && (
            <button
              onClick={() => setActiveTab("teacher_knowledge")}
              className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
                activeTab === "teacher_knowledge" ? "!bg-brand-yellow !shadow-hard-sm" : ""
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-brand-cyan" />
              <span>Instructor Materials &amp; Uploads</span>
            </button>
          )}
        </nav>

        {/* Tab Content Display */}
        <main className="pb-16">
          {activeTab === "tutor" && (
            <TutorTab
              course={selectedCourse}
              currentUser={currentUser}
              hasActiveScoredAssessment={!!activeScoredAssessmentId}
            />
          )}

          {activeTab === "revisor" && (
            <RevisorTab
              course={selectedCourse}
              topics={topics}
              currentUser={currentUser}
              hasActiveScoredAssessment={!!activeScoredAssessmentId}
              onToggleLockout={() =>
                setActiveScoredAssessmentId((prev) =>
                  prev ? null : "simulated-scored-assessment-in-progress"
                )
              }
              targetObjective={targetObjectiveForPractice}
            />
          )}

          {activeTab === "curriculum" && (
            <CurriculumTab
              course={selectedCourse}
              topics={topics}
              onSelectObjectiveForPractice={(obj) =>
                handleSwitchToRevisorWithObjective(obj)
              }
            />
          )}

          {activeTab === "mastery" && (
            <MasteryDiagnosisTab
              course={selectedCourse}
              currentUser={currentUser}
              onStartProbingPlan={() => {
                setMentorMode("revisor");
                setActiveTab("revisor");
              }}
            />
          )}

          {activeTab === "scheduling" && (
            <SchedulingTab
              course={selectedCourse}
              currentUser={currentUser}
              onStartRetentionSession={() => {
                setMentorMode("revisor");
                setActiveTab("revisor");
              }}
            />
          )}

          {activeTab === "teacher_knowledge" && isInstructor && (
            <KnowledgeTab course={selectedCourse} />
          )}
        </main>
      </div>
      )}

      {/* Footer Gateway Info */}
      <footer className="mt-auto border-t-2 border-ink/10 bg-surface-warm/40 py-6 px-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs font-medium text-ink-muted">
          <div className="flex items-center gap-2">
            <span className="font-bold text-ink">Recall Platform:</span>
            <span>Deterministic Mastery &amp; Collaborative SLM Grounding</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Environment: {health?.environment || "development"}</span>
            <span>Version: {health?.version || "0.1.0"}</span>
            <span>Engine: {readiness?.status || "ready"}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
