"use client";

import React, { useEffect, useState } from "react";
import {
  BookOpen,
  Brain,
  Calendar,
  Compass,
  FileCheck2,
  FileText,
  HelpCircle,
  Layers,
  MessageSquare,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import {
  clearStoredToken,
  getStoredToken,
  recallApi,
  setStoredToken,
} from "../lib/api-client";
import {
  CourseResponse,
  DiagnosticSessionPlanResponse,
  HealthResponse,
  LearningObjectiveResponse,
  ReadinessResponse,
  RetentionSessionPlanResponse,
  TopicResponse,
  UserResponse,
} from "../types";
import { CurriculumTab } from "../components/CurriculumTab";
import { KnowledgeTab } from "../components/KnowledgeTab";
import { MasteryDiagnosisTab } from "../components/MasteryDiagnosisTab";
import { Navbar } from "../components/Navbar";
import { PracticeTab } from "../components/PracticeTab";
import { RevisorTab } from "../components/RevisorTab";
import { SchedulingTab } from "../components/SchedulingTab";
import { TutorTab } from "../components/TutorTab";

type ActiveTab =
  | "curriculum"
  | "mastery"
  | "knowledge"
  | "practice"
  | "tutor"
  | "revisor"
  | "scheduling";

export default function HomePage() {
  // Global Platform State
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [currentUser, setCurrentUser] = useState<UserResponse | null>(null);
  const [courses, setCourses] = useState<CourseResponse[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<CourseResponse | null>(null);
  const [topics, setTopics] = useState<TopicResponse[]>([]);

  // Navigation State
  const [activeTab, setActiveTab] = useState<ActiveTab>("curriculum");
  const [isSeeding, setIsSeeding] = useState<boolean>(false);
  const [activeScoredAssessmentId, setActiveScoredAssessmentId] = useState<string | null>(null);
  const [targetObjectiveForPractice, setTargetObjectiveForPractice] =
    useState<LearningObjectiveResponse | null>(null);

  // Initialize Auth & Data
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
        // Auto-seed DBMS course if empty catalog
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

      // If no user is logged in, perform seamless demo student login
      if (!token) {
        try {
          const demoResp = await recallApi.demoLogin("student", "CS340");
          setStoredToken(demoResp.access_token);
          setCurrentUser(demoResp.user);
        } catch {
          // ignore offline probe
        }
      }
    } catch (err) {
      console.error("Initialization error:", err);
    }
  };

  useEffect(() => {
    initializePlatform();
  }, []);

  // Course Selection Change Handler
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
  const handleDemoLogin = async (role: "student" | "instructor") => {
    try {
      const resp = await recallApi.demoLogin(role, selectedCourse?.code || "CS340");
      setStoredToken(resp.access_token);
      setCurrentUser(resp.user);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to switch demo identity.");
    }
  };

  // Logout Handler
  const handleLogout = () => {
    clearStoredToken();
    setCurrentUser(null);
  };

  // Seed DBMS Handler
  const handleSeedCourse = async () => {
    setIsSeeding(true);
    try {
      await recallApi.seedDbmsCourse();
      const courseList = await recallApi.listCourses();
      setCourses(courseList);
      if (courseList.length > 0) {
        handleSelectCourse(courseList[0]);
      }
      alert("Successfully seeded CS340 DBMS curriculum and verified question bank!");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to seed course.");
    } finally {
      setIsSeeding(false);
    }
  };

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
          isSeeding={isSeeding}
          hasActiveScoredAssessment={!!activeScoredAssessmentId}
        />
      </div>

      {/* Main Tabbed Navigation */}
      <div className="max-w-7xl mx-auto w-full px-4 py-6">
        <nav className="flex flex-wrap items-center gap-2 pb-4 border-b-2 border-ink/10">
          <button
            onClick={() => setActiveTab("curriculum")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "curriculum" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Curriculum & Overview</span>
          </button>

          <button
            onClick={() => setActiveTab("mastery")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "mastery" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <Brain className="w-3.5 h-3.5 text-brand-green" />
            <span>Mastery & Diagnosis</span>
          </button>

          <button
            onClick={() => setActiveTab("knowledge")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "knowledge" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <FileText className="w-3.5 h-3.5 text-brand-cyan" />
            <span>Knowledge & Materials</span>
          </button>

          <button
            onClick={() => setActiveTab("practice")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "practice" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-brand-coral" />
            <span>Practice & Lockout</span>
          </button>

          <button
            onClick={() => setActiveTab("tutor")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "tutor" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-brand-yellow" />
            <span>AI Tutor (SLM A)</span>
          </button>

          <button
            onClick={() => setActiveTab("revisor")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "revisor" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <FileCheck2 className="w-3.5 h-3.5 text-brand-coral" />
            <span>Revisor Audit (SLM B)</span>
          </button>

          <button
            onClick={() => setActiveTab("scheduling")}
            className={`tactile-btn-white text-xs py-2 px-3.5 font-bold ${
              activeTab === "scheduling" ? "!bg-brand-yellow !shadow-hard-sm" : ""
            }`}
          >
            <Calendar className="w-3.5 h-3.5 text-brand-cyan" />
            <span>Spaced Scheduling (Rule 6)</span>
          </button>
        </nav>

        {/* Tab Content Display */}
        <main className="mt-6 pb-16">
          {activeTab === "curriculum" && (
            <CurriculumTab
              course={selectedCourse}
              topics={topics}
              onSelectObjectiveForPractice={(obj) => {
                setTargetObjectiveForPractice(obj);
                setActiveTab("practice");
              }}
            />
          )}

          {activeTab === "mastery" && (
            <MasteryDiagnosisTab
              course={selectedCourse}
              currentUser={currentUser}
              onStartProbingPlan={() => {
                setActiveTab("practice");
              }}
            />
          )}

          {activeTab === "knowledge" && <KnowledgeTab course={selectedCourse} />}

          {activeTab === "practice" && (
            <PracticeTab
              course={selectedCourse}
              topics={topics}
              currentUser={currentUser}
              activeScoredAssessmentId={activeScoredAssessmentId}
              setActiveScoredAssessmentId={setActiveScoredAssessmentId}
              targetObjective={targetObjectiveForPractice}
            />
          )}

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
              currentUser={currentUser}
              hasActiveScoredAssessment={!!activeScoredAssessmentId}
            />
          )}

          {activeTab === "scheduling" && (
            <SchedulingTab
              course={selectedCourse}
              currentUser={currentUser}
              onStartRetentionSession={() => {
                setActiveTab("practice");
              }}
            />
          )}
        </main>
      </div>

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
