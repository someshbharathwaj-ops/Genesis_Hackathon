"use client";

import React, { useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  Lock,
  LogOut,
  RefreshCw,
  Shield,
  Sparkles,
  User,
  Users,
} from "lucide-react";
import { CourseResponse, UserResponse } from "../types";

interface NavbarProps {
  currentUser: UserResponse | null;
  courses: CourseResponse[];
  selectedCourse: CourseResponse | null;
  onSelectCourse: (course: CourseResponse) => void;
  onLoginDemo: (role: "student" | "instructor") => void;
  onLogout: () => void;
  onSeedCourse: () => void;
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
  isSeeding,
  hasActiveScoredAssessment,
}: NavbarProps) {
  const [showUserMenu, setShowUserMenu] = useState(false);

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

          {/* Seed DBMS Button */}
          <button
            onClick={onSeedCourse}
            disabled={isSeeding}
            className="tactile-btn-white text-xs py-1.5 px-3"
            title="Seed CS340 DBMS Curriculum & Questions"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? "animate-spin" : ""}`} />
            <span>{isSeeding ? "Seeding..." : "Seed DBMS"}</span>
          </button>

          {/* User Auth Info & Switcher */}
          {currentUser ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="tactile-btn-yellow text-xs py-1.5 px-3"
              >
                <User className="w-3.5 h-3.5" />
                <span>{currentUser.full_name}</span>
                <span className="tactile-tag bg-surface text-ink text-[9px] py-0 px-1 ml-1 uppercase">
                  {currentUser.role}
                </span>
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
                    <Shield className="w-3.5 h-3.5 text-brand-coral" />
                    <span>Demo Instructor (Prof. Codd)</span>
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
    </header>
  );
}
