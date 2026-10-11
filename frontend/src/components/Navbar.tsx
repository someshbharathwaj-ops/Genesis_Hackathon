import React, { useEffect, useState } from "react";
import {
  Bell,
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
import { CourseResponse, InAppNotificationResponse, UserResponse } from "../types";
import { recallApi } from "../lib/api-client";

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
  const [notifications, setNotifications] = useState<InAppNotificationResponse[]>([]);
  const [showNotifMenu, setShowNotifMenu] = useState(false);

  useEffect(() => {
    if (currentUser?.id && currentUser.role === "student") {
      recallApi.getStudentNotifications(currentUser.id).then(setNotifications).catch(() => {});
      const interval = setInterval(() => {
        recallApi.getStudentNotifications(currentUser.id).then(setNotifications).catch(() => {});
      }, 15000);
      return () => clearInterval(interval);
    }
  }, [currentUser?.id, currentUser?.role]);

  const unreadNotifs = notifications.filter((n) => !n.is_read);

  const handleMarkRead = async (notifId: string) => {
    if (!currentUser?.id) return;
    try {
      await recallApi.markNotificationRead(currentUser.id, notifId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, is_read: true } : n))
      );
    } catch {}
  };

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

          {/* Dynamic Seed Course & Create Course Controls (Instructor & Admin Only) */}
          {currentUser?.role !== "student" && (
            <>
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
            </>
          )}

          {/* User Auth Profile & Sign Out (Mandatory sign-out to switch role) */}
          {currentUser ? (
            <div className="flex items-center gap-2">
              {/* In-App Notifications Bell for Students */}
              {currentUser.role === "student" && (
                <div className="relative">
                  <button
                    id="btn-notifications"
                    onClick={() => setShowNotifMenu(!showNotifMenu)}
                    className="tactile-btn-white text-xs py-1.5 px-2.5 flex items-center gap-1.5 font-bold relative"
                    title="In-App Assessment Alerts"
                  >
                    <Bell className="w-3.5 h-3.5 text-ink" />
                    {unreadNotifs.length > 0 && (
                      <span className="w-4 h-4 rounded-full bg-brand-coral text-white text-[9px] font-black flex items-center justify-center -ml-0.5">
                        {unreadNotifs.length}
                      </span>
                    )}
                  </button>

                  {showNotifMenu && (
                    <div className="absolute right-0 mt-2 w-80 tactile-card p-3 z-50 flex flex-col gap-2 max-h-96 overflow-y-auto">
                      <div className="flex items-center justify-between pb-2 border-b-2 border-ink/10">
                        <span className="font-black text-xs text-ink flex items-center gap-1.5">
                          <Bell className="w-3.5 h-3.5 text-brand-coral" />
                          <span>Assessment Alerts</span>
                        </span>
                        <span className="text-[10px] font-bold text-ink-muted">
                          {unreadNotifs.length} Unread
                        </span>
                      </div>

                      {notifications.length === 0 ? (
                        <p className="text-xs text-ink-muted text-center py-4 font-medium">
                          No alerts right now. You are fully up to date!
                        </p>
                      ) : (
                        notifications.map((n) => (
                          <div
                            key={n.id}
                            className={`p-2.5 rounded border text-xs flex flex-col gap-1 ${
                              n.is_read
                                ? "bg-surface-warm/30 border-ink/10 text-ink-muted"
                                : "bg-white border-brand-coral shadow-hard-sm text-ink"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <span className="font-bold text-ink text-[11px] leading-tight">
                                {n.title}
                              </span>
                              {!n.is_read && (
                                <button
                                  onClick={() => handleMarkRead(n.id)}
                                  className="text-[9px] font-black text-brand-coral hover:underline shrink-0"
                                >
                                  Mark Read
                                </button>
                              )}
                            </div>
                            <p className="text-[11px] text-ink-muted leading-tight">{n.message}</p>
                            {n.created_at && (
                              <span className="text-[9px] text-ink-faint">
                                {new Date(n.created_at).toLocaleDateString()}
                              </span>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="relative">
                <button
                  id="btn-user-profile"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="tactile-btn-white text-xs py-1.5 px-3 flex items-center gap-1.5 font-bold"
                >
                  <User className="w-3.5 h-3.5 text-ink-muted" />
                  <span className="font-black text-ink">{currentUser.full_name}</span>
                  <span
                    className={`tactile-tag text-[9px] py-0 px-1.5 uppercase font-black ${
                      currentUser.role === "admin"
                        ? "bg-brand-green text-ink"
                        : currentUser.role === "instructor"
                        ? "bg-brand-coral text-white"
                        : "bg-brand-yellow text-ink"
                    }`}
                  >
                    {currentUser.role}
                  </span>
                </button>

                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-56 tactile-card p-3 z-50 flex flex-col gap-2">
                    <div className="text-xs pb-2 border-b-2 border-ink/10">
                      <div className="font-bold text-ink">{currentUser.full_name}</div>
                      <div className="text-ink-muted text-[11px] truncate">{currentUser.email}</div>
                      <div className="text-[10px] uppercase font-black text-ink-muted mt-1">
                        Active Mode: {currentUser.role}
                      </div>
                    </div>

                    <p className="text-[10px] text-ink-muted leading-tight">
                      To switch between Student, Instructor, and Admin modes, sign out below.
                    </p>

                    <button
                      onClick={() => {
                        onLogout();
                        setShowUserMenu(false);
                      }}
                      className="tactile-btn-coral text-xs py-1.5 w-full font-black flex items-center justify-center gap-1.5"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Direct Sign Out Button */}
              <button
                id="btn-nav-logout"
                onClick={onLogout}
                title="Sign out to switch mode or exit"
                className="tactile-btn-coral text-xs py-1.5 px-3 flex items-center gap-1.5 font-black hover:opacity-90"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign Out</span>
              </button>
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
