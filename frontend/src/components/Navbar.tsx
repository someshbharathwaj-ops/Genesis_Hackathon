"use client";

import React, { useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  GraduationCap,
  Lock,
  LogOut,
  Plus,
  RefreshCw,
  Shield,
  Sparkles,
  User,
  UserCheck,
  Users,
  X,
} from "lucide-react";
import { CourseResponse, UserResponse } from "../types";

interface NavbarProps {
  currentUser: UserResponse | null;
  courses: CourseResponse[];
  selectedCourse: CourseResponse | null;
  onSelectCourse: (course: CourseResponse) => void;
  onLoginDemo: (role: "student" | "instructor" | "admin") => void;
  onLogout: () => void;
  onSeedCourse: (courseCode?: string) => void;
  onSeedNewCourse?: (payload: { code: string; title: string; description?: string }) => void;
  isSeeding: boolean;
  hasActiveScoredAssessment: boolean;
}

export function Navbar({
  currentUser,
  courses,
  selectedCourse,
  onSelectCourse,
  onLoginDemo,
  onLogout,
  onSeedCourse,
  onSeedNewCourse,
  isSeeding,
  hasActiveScoredAssessment,
}: NavbarProps) {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNewCourseModal, setShowNewCourseModal] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");

  return (
    <header className="tactile-card-warm p-4 md:p-5 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-friendly-sm bg-brand-yellow border-2 border-ink shadow-hard-sm flex items-center justify-center font-black text-xl">
            R
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-black tracking-tight text-ink">Recall</span>
              <span className="tactile-tag bg-brand-yellow text-ink text-[10px] py-0 px-1.5">
                SLM VERIFIED
              </span>
            </div>
            <p className="text-xs text-ink-muted font-medium">
              Course-Aware Grounded Adaptive Learning
            </p>
          </div>
        </div>

        {/* Global Alert if Active Assessment Lockout is Engaged */}
        {hasActiveScoredAssessment && (
          <div className="flex items-center gap-2 bg-brand-coral/15 border-2 border-brand-coral px-3 py-1.5 rounded-friendly-sm text-xs font-bold text-ink animate-pulse">
            <Lock className="w-4 h-4 text-brand-coral" />
            <span>ASSESSMENT LOCKOUT ACTIVE: AI Assistance Disabled (ADR 0002)</span>
          </div>
        )}

        {/* Course & Identity Selectors */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Course Switcher */}
          <div className="flex items-center gap-2 bg-surface px-3 py-1.5 border-2 border-ink rounded-friendly-sm shadow-hard-sm">
            <BookOpen className="w-4 h-4 text-brand-cyan" />
            <select
              value={selectedCourse?.id || ""}
              onChange={(e) => {
                const found = courses.find((c) => c.id === e.target.value);
                if (found) onSelectCourse(found);
              }}
              className="bg-transparent text-xs font-bold text-ink outline-none cursor-pointer"
            >
              {courses.length === 0 ? (
                <option value="">No Courses Seeded</option>
              ) : (
                courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code}: {c.title}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Dynamic Seed Active Course Button */}
          <button
            id="btn-seed-active-course"
            onClick={() => onSeedCourse(selectedCourse?.code)}
            disabled={isSeeding}
            className="tactile-btn-white text-xs py-1.5 px-3 flex items-center gap-1.5 font-bold"
            title={`Seed ${selectedCourse?.code || "Current"} Curriculum & Knowledge Base`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? "animate-spin" : ""}`} />
            <span>{isSeeding ? "Seeding..." : `Seed ${selectedCourse ? selectedCourse.code : "Course"}`}</span>
          </button>

          {/* Seed / Create New Course Trigger */}
          <button
            id="btn-seed-new-course"
            onClick={() => setShowNewCourseModal(true)}
            disabled={isSeeding}
            className="tactile-btn-yellow text-xs py-1.5 px-3 flex items-center gap-1.5 font-bold"
            title="Seed a new or custom course"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>+ New Course</span>
          </button>

          {/* 1-Click Direct Role Switcher (Zero sign-out needed) */}
          <div className="flex items-center bg-surface border-2 border-ink p-0.5 rounded-friendly-sm shadow-hard-sm">
            <button
              id="nav-role-student"
              type="button"
              onClick={() => onLoginDemo("student")}
              className={`px-2 py-1 text-xs font-bold rounded flex items-center gap-1 transition-all ${
                currentUser?.role === "student"
                  ? "bg-brand-yellow text-ink shadow-hard-sm"
                  : "text-ink-muted hover:text-ink hover:bg-surface-warm"
              }`}
              title="Switch directly to Student Mode"
            >
              <GraduationCap className="w-3.5 h-3.5" />
              <span>Student</span>
            </button>
            <button
              id="nav-role-instructor"
              type="button"
              onClick={() => onLoginDemo("instructor")}
              className={`px-2 py-1 text-xs font-bold rounded flex items-center gap-1 transition-all ${
                currentUser?.role === "instructor"
                  ? "bg-brand-coral text-white shadow-hard-sm"
                  : "text-ink-muted hover:text-ink hover:bg-surface-warm"
              }`}
              title="Switch directly to Instructor Mode"
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Instructor</span>
            </button>
            <button
              id="nav-role-admin"
              type="button"
              onClick={() => onLoginDemo("admin")}
              className={`px-2 py-1 text-xs font-bold rounded flex items-center gap-1 transition-all ${
                currentUser?.role === "admin"
                  ? "bg-brand-green text-ink shadow-hard-sm"
                  : "text-ink-muted hover:text-ink hover:bg-surface-warm"
              }`}
              title="Switch directly to Admin & Audit Mode"
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Admin</span>
            </button>
          </div>

          {/* User Auth Info & Switcher */}
          {currentUser ? (
            <div className="relative">
              <button
                id="btn-user-profile"
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="tactile-btn-yellow text-xs py-1.5 px-3"
              >
                <User className="w-3.5 h-3.5" />
                <span>{currentUser.full_name}</span>
                <span className="tactile-tag bg-surface text-ink text-[9px] py-0 px-1 ml-1 uppercase">
                  {currentUser.role}
                </span>
              </button>

              <button
                id="btn-nav-logout"
                onClick={onLogout}
                title="Sign out of current session"
                className="tactile-btn-white text-xs py-1.5 px-2.5 font-bold hover:!bg-brand-coral hover:!text-white"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-64 tactile-card p-3 z-50 flex flex-col gap-2">
                  <div className="text-xs pb-2 border-b-2 border-ink/10">
                    <div className="font-bold text-ink">{currentUser.full_name}</div>
                    <div className="text-ink-muted text-[11px]">{currentUser.email}</div>
                  </div>

                  <div className="text-[11px] font-bold text-ink-muted uppercase tracking-wider pt-1">
                    Switch Demo Identity
                  </div>
                  <button
                    onClick={() => {
                      onLoginDemo("student");
                      setShowUserMenu(false);
                    }}
                    className="tactile-btn-white text-xs py-1 text-left justify-start"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-brand-green" />
                    <span>Demo Student (Ada Lovelace)</span>
                  </button>
                  <button
                    onClick={() => {
                      onLoginDemo("instructor");
                      setShowUserMenu(false);
                    }}
                    className="tactile-btn-white text-xs py-1 text-left justify-start"
                  >
                    <UserCheck className="w-3.5 h-3.5 text-brand-coral" />
                    <span>Demo Instructor (Prof. Faculty)</span>
                  </button>
                  <button
                    onClick={() => {
                      onLoginDemo("admin");
                      setShowUserMenu(false);
                    }}
                    className="tactile-btn-white text-xs py-1 text-left justify-start"
                  >
                    <Shield className="w-3.5 h-3.5 text-brand-green" />
                    <span>Demo Admin (Auditor Console)</span>
                  </button>

                  <div className="pt-2 border-t-2 border-ink/10">
                    <button
                      onClick={() => {
                        onLogout();
                        setShowUserMenu(false);
                      }}
                      className="tactile-btn-coral text-xs py-1 w-full"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onLoginDemo("student")}
                className="tactile-btn-yellow text-xs py-1.5 px-3"
              >
                <Users className="w-3.5 h-3.5" />
                <span>Demo Student Login</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Seed New Course Modal */}
      {showNewCourseModal && (
        <div className="fixed inset-0 bg-ink/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="tactile-card-warm max-w-md w-full p-6 flex flex-col gap-5 border-2 border-ink shadow-hard-lg">
            <div className="flex items-center justify-between pb-3 border-b-2 border-ink/10">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-brand-yellow" />
                <h3 className="font-black text-lg text-ink">Seed & Initialize Course</h3>
              </div>
              <button
                onClick={() => setShowNewCourseModal(false)}
                className="p-1 hover:bg-ink/10 rounded transition-colors"
              >
                <X className="w-4 h-4 text-ink-muted" />
              </button>
            </div>

            {/* Quick Presets */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-bold text-ink-muted uppercase tracking-wider">
                Quick Catalog Presets
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setNewCode("CS301");
                    setNewTitle("Operating Systems & Concurrency");
                    setNewDescription(
                      "Process management, CPU scheduling, synchronization, and deadlocks."
                    );
                  }}
                  className="tactile-btn-white text-xs py-1 px-2 text-left justify-start"
                >
                  ⚡ CS301 (OS)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNewCode("CS340");
                    setNewTitle("Database Management Systems");
                    setNewDescription(
                      "Relational data model, functional dependencies, and normal forms."
                    );
                  }}
                  className="tactile-btn-white text-xs py-1 px-2 text-left justify-start"
                >
                  ⚡ CS340 (DBMS)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNewCode("CS305");
                    setNewTitle("Computer Networks");
                    setNewDescription(
                      "OSI and TCP/IP models, routing protocols, flow control, and sockets."
                    );
                  }}
                  className="tactile-btn-white text-xs py-1 px-2 text-left justify-start"
                >
                  ⚡ CS305 (Networks)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setNewCode("CS410");
                    setNewTitle("Artificial Intelligence & ML");
                    setNewDescription(
                      "Search algorithms, heuristic evaluation, and reinforcement learning."
                    );
                  }}
                  className="tactile-btn-white text-xs py-1 px-2 text-left justify-start"
                >
                  ⚡ CS410 (AI/ML)
                </button>
              </div>
            </div>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!newCode.trim() || !newTitle.trim()) return;
                if (onSeedNewCourse) {
                  await onSeedNewCourse({
                    code: newCode.trim().toUpperCase(),
                    title: newTitle.trim(),
                    description: newDescription.trim() || undefined,
                  });
                } else {
                  onSeedCourse(newCode.trim().toUpperCase());
                }
                setShowNewCourseModal(false);
                setNewCode("");
                setNewTitle("");
                setNewDescription("");
              }}
              className="flex flex-col gap-3.5"
            >
              <div className="flex flex-col gap-1">
                <label className="text-xs font-bold text-ink">
                  Course Code <span className="text-brand-coral">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newCode}
                  onChange={(e) => setNewCode(e.target.value)}
                  placeholder="e.g. CS301 or CS305"
                  className="tactile-input text-xs py-1.5 px-3 font-mono font-bold"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-bold text-ink">
                  Course Title <span className="text-brand-coral">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Operating Systems & Concurrency"
                  className="tactile-input text-xs py-1.5 px-3"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-bold text-ink">
                  Course Description (Optional)
                </label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Key topics, prerequisites, and learning objectives..."
                  rows={2}
                  className="tactile-input text-xs py-1.5 px-3 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t-2 border-ink/10">
                <button
                  type="button"
                  onClick={() => setShowNewCourseModal(false)}
                  className="tactile-btn-white text-xs py-1.5 px-3"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSeeding || !newCode.trim() || !newTitle.trim()}
                  className="tactile-btn-yellow text-xs py-1.5 px-4 flex items-center gap-1.5 font-bold"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? "animate-spin" : ""}`} />
                  <span>{isSeeding ? "Seeding..." : "Seed & Initialize"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
}
