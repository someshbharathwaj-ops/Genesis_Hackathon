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
}

export function LoginView({
  onLoginSuccess,
}: LoginViewProps) {
  const [email, setEmail] = useState("student@recall.edu");
  const [password, setPassword] = useState("student123");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleManualSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setErrorMessage("Please enter both institutional email and password.");
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const resp = await recallApi.login(email.trim(), password.trim());
      setStoredToken(resp.access_token);
      onLoginSuccess(resp.user);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Invalid institutional credentials. Please check your email and password."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleFillCredentials = (fillEmail: string, fillPass: string) => {
    setEmail(fillEmail);
    setPassword(fillPass);
    setErrorMessage(null);
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
              PORTAL SIGN-IN
            </span>
          </div>
          <p className="text-sm font-medium text-ink-muted max-w-sm">
            Course-aware adaptive learning platform with role-isolated Student, Instructor, and Admin workspaces.
          </p>
        </div>

        {/* Auth Box */}
        <div className="tactile-card p-6 flex flex-col gap-5 bg-surface">
          <div className="flex items-center justify-between border-b border-ink/10 pb-3">
            <span className="text-xs font-black uppercase tracking-wider text-ink">
              Institutional Authentication
            </span>
            <span className="tactile-tag bg-brand-cyan/20 text-brand-cyan text-[10px]">
              Session Protected
            </span>
          </div>

          {errorMessage && (
            <div className="p-3 bg-brand-coral/15 border-2 border-brand-coral rounded-friendly-sm text-xs font-bold text-ink">
              {errorMessage}
            </div>
          )}

          {/* Showcase Credentials Selector */}
          <div className="flex flex-col gap-2 p-3 bg-surface-warm/30 border-2 border-ink rounded-friendly-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-ink">
                Demo Accounts &amp; Passwords:
              </span>
              <span className="text-[10px] text-ink-muted">Click to populate</span>
            </div>

            <div className="flex flex-col gap-1.5">
              {/* Student */}
              <button
                type="button"
                id="btn-fill-student"
                onClick={() => handleFillCredentials("student@recall.edu", "student123")}
                className={`p-2 border rounded text-left flex items-center justify-between text-xs transition-all ${
                  email === "student@recall.edu"
                    ? "bg-brand-yellow/30 border-ink font-bold shadow-hard-sm"
                    : "bg-surface hover:bg-surface-warm border-ink/20 font-medium"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <GraduationCap className="w-3.5 h-3.5 text-brand-yellow" />
                  <span className="font-bold text-ink">Student:</span>
                  <span className="font-mono text-[11px] text-ink-muted">student@recall.edu</span>
                </div>
                <span className="font-mono text-[10px] bg-brand-yellow px-1.5 py-0.5 rounded font-bold text-ink">
                  student123
                </span>
              </button>

              {/* Teacher / Instructor */}
              <button
                type="button"
                id="btn-fill-instructor"
                onClick={() => handleFillCredentials("instructor@recall.edu", "instructor123")}
                className={`p-2 border rounded text-left flex items-center justify-between text-xs transition-all ${
                  email === "instructor@recall.edu"
                    ? "bg-brand-coral/20 border-ink font-bold shadow-hard-sm"
                    : "bg-surface hover:bg-surface-warm border-ink/20 font-medium"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-brand-coral" />
                  <span className="font-bold text-ink">Teacher:</span>
                  <span className="font-mono text-[11px] text-ink-muted">instructor@recall.edu</span>
                </div>
                <span className="font-mono text-[10px] bg-brand-coral text-white px-1.5 py-0.5 rounded font-bold">
                  instructor123
                </span>
              </button>

              {/* Admin */}
              <button
                type="button"
                id="btn-fill-admin"
                onClick={() => handleFillCredentials("admin@recall.edu", "admin123")}
                className={`p-2 border rounded text-left flex items-center justify-between text-xs transition-all ${
                  email === "admin@recall.edu"
                    ? "bg-brand-green/20 border-ink font-bold shadow-hard-sm"
                    : "bg-surface hover:bg-surface-warm border-ink/20 font-medium"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-brand-green" />
                  <span className="font-bold text-ink">Admin:</span>
                  <span className="font-mono text-[11px] text-ink-muted">admin@recall.edu</span>
                </div>
                <span className="font-mono text-[10px] bg-brand-green text-ink px-1.5 py-0.5 rounded font-bold">
                  admin123
                </span>
              </button>
            </div>
          </div>

          {/* Standard Login Form */}
          <form onSubmit={handleManualSignIn} className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-ink-muted" />
                <span>Institutional Email</span>
              </label>
              <input
                id="input-login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@recall.edu"
                className="tactile-input text-xs font-mono font-bold"
                disabled={isLoading}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-ink flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-ink-muted" />
                <span>Password</span>
              </label>
              <input
                id="input-login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="tactile-input text-xs font-mono font-bold"
                disabled={isLoading}
              />
            </div>

            <button
              id="btn-submit-login"
              type="submit"
              disabled={isLoading}
              className="tactile-btn-yellow mt-2 py-2.5 text-xs font-black flex items-center justify-center gap-2"
            >
              <LogIn className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>{isLoading ? "Authenticating..." : "Sign In to Recall"}</span>
            </button>
          </form>

          <p className="text-[10px] text-ink-muted text-center leading-tight">
            Note: Changing roles requires signing out of your current session.
          </p>
        </div>

        {/* Grounding Footer */}
        <div className="text-center text-[11px] font-medium text-ink-muted flex items-center justify-center gap-2">
          <Shield className="w-3.5 h-3.5 text-brand-green" />
          <span>Institutional Role Separation &bull; Sign-Out Required to Switch</span>
        </div>
      </div>
    </div>
  );
}
