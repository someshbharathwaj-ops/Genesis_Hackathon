"use client";

import React, { useState } from "react";
import {
  BookOpen,
  GraduationCap,
  KeyRound,
  LogIn,
  Mail,
  Shield,
  Sparkles,
  UserCheck,
} from "lucide-react";
import { CourseResponse, UserResponse } from "../types";
import { recallApi, setStoredToken } from "../lib/api-client";

interface LoginViewProps {
  onLoginSuccess: (user: UserResponse) => void;
  selectedCourseCode: string;
  courses?: CourseResponse[];
  onSelectCourse?: (course: CourseResponse) => void;
}

export function LoginView({
  onLoginSuccess,
  selectedCourseCode,
  courses,
  onSelectCourse,
}: LoginViewProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDemoSignIn = async (role: "student" | "instructor") => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const resp = await recallApi.demoLogin(role, selectedCourseCode || "CS340");
      setStoredToken(resp.access_token);
      onLoginSuccess(resp.user);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to sign in with demo credentials."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setErrorMessage("Please enter both email and password.");
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const resp = await recallApi.login(email.trim());
      setStoredToken(resp.access_token);
      onLoginSuccess(resp.user);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Invalid credentials or unauthorized login."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md flex flex-col gap-6">
        {/* Brand Header */}
        <div className="text-center flex flex-col items-center gap-2">
          <div className="w-14 h-14 rounded-friendly-sm bg-brand-yellow border-2 border-ink shadow-hard flex items-center justify-center font-black text-2xl text-ink">
            R
          </div>
          <div className="flex items-center gap-2 mt-1">
            <h1 className="text-3xl font-black text-ink tracking-tight">Recall</h1>
            <span className="tactile-tag bg-brand-yellow text-ink text-xs py-0.5 px-2">
              AI MENTOR
            </span>
          </div>
          <p className="text-sm font-medium text-ink-muted max-w-sm">
            Course-aware adaptive learning platform with grounded Tutor and Revisor modes.
          </p>
        </div>

        {/* Auth Box */}
        <div className="tactile-card p-6 flex flex-col gap-6 bg-surface">
          <div className="flex items-center justify-between border-b border-ink/10 pb-3">
            <span className="text-xs font-black uppercase tracking-wider text-ink">
              Institutional Sign-In
            </span>
            <span className="tactile-tag bg-brand-cyan/20 text-brand-cyan text-[10px]">
              Secure Session
            </span>
          </div>

          {errorMessage && (
            <div className="p-3 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm text-xs font-bold text-ink">
              {errorMessage}
            </div>
          )}

          {/* Active Target Course Selection */}
          {courses && courses.length > 0 && (
            <div className="flex flex-col gap-1.5 p-3 bg-surface-warm/40 border border-ink/20 rounded-friendly-sm">
              <div className="flex items-center justify-between text-xs font-bold">
                <span className="text-ink-muted flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-brand-cyan" />
                  <span>Enrolled Course:</span>
                </span>
                <span className="font-mono font-black text-brand-cyan bg-brand-cyan/15 px-1.5 py-0.5 rounded">
                  {selectedCourseCode}
                </span>
              </div>
              <select
                value={selectedCourseCode}
                onChange={(e) => {
                  const found = courses.find((c) => c.code === e.target.value);
                  if (found && onSelectCourse) onSelectCourse(found);
                }}
                className="tactile-select text-xs py-1.5 px-2 font-bold bg-white w-full cursor-pointer"
              >
                {courses.map((c) => (
                  <option key={c.id} value={c.code}>
                    {c.code} &mdash; {c.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* 1-Click Demo Profiles */}
          <div className="flex flex-col gap-2.5">
            <label className="text-xs font-bold text-ink-muted">
              Select Demo Identity:
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                id="btn-demo-student"
                type="button"
                onClick={() => handleDemoSignIn("student")}
                disabled={isLoading}
                className="tactile-btn-white flex flex-col items-start p-3 text-left hover:border-brand-yellow"
              >
                <div className="flex items-center gap-1.5 text-xs font-black text-ink">
                  <GraduationCap className="w-4 h-4 text-brand-yellow" />
                  <span>Student</span>
                </div>
                <span className="text-[10px] text-ink-muted font-medium mt-0.5">
                  Ada Lovelace (CS340)
                </span>
              </button>

              <button
                id="btn-demo-instructor"
                type="button"
                onClick={() => handleDemoSignIn("instructor")}
                disabled={isLoading}
                className="tactile-btn-white flex flex-col items-start p-3 text-left hover:border-brand-coral"
              >
                <div className="flex items-center gap-1.5 text-xs font-black text-ink">
                  <UserCheck className="w-4 h-4 text-brand-coral" />
                  <span>Instructor</span>
                </div>
                <span className="text-[10px] text-ink-muted font-medium mt-0.5">
                  Prof. E. F. Codd
                </span>
              </button>
            </div>
          </div>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-ink/10"></div>
            <span className="flex-shrink mx-3 text-[10px] font-bold text-ink-faint uppercase">
              Or password sign-in
            </span>
            <div className="flex-grow border-t border-ink/10"></div>
          </div>

          {/* Standard Login Form */}
          <form onSubmit={handleManualSignIn} className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-ink-muted" />
                <span>Institutional Email</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student.ada@recall.edu"
                className="tactile-input text-xs"
                disabled={isLoading}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-ink-muted" />
                <span>Password</span>
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="tactile-input text-xs"
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="tactile-btn-yellow mt-2 py-2.5 text-xs font-black"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>{isLoading ? "Signing In..." : "Sign In to Recall"}</span>
            </button>
          </form>
        </div>

        {/* Grounding Footer */}
        <div className="text-center text-[11px] font-medium text-ink-muted flex items-center justify-center gap-2">
          <Shield className="w-3.5 h-3.5 text-brand-green" />
          <span>Syllabus Bound &bull; Deterministic Grader Authority</span>
        </div>
      </div>
    </div>
  );
}
