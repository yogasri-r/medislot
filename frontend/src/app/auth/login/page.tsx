"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Activity, Lock, Mail, AlertCircle, Sparkles, ArrowRight, UserCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login, loginAsPreset, isLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/my-appointments");
    } catch (err: any) {
      setError(err.message || "Invalid credentials. Please verify your email and password.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickLogin = async (role: "patient" | "doctor" | "admin") => {
    setError(null);
    setSubmitting(true);
    try {
      await loginAsPreset(role);
      if (role === "doctor") {
        router.push("/doctor/dashboard");
      } else {
        router.push("/my-appointments");
      }
    } catch (err: any) {
      setError(err.message || "Failed to authenticate demo persona.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center">
          <Link href="/" className="inline-flex items-center gap-2 mb-4 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500 p-2 shadow-lg shadow-teal-500/20">
              <Activity className="h-6 w-6 text-slate-950 stroke-[2.5]" />
            </div>
            <span className="text-2xl font-bold tracking-tight text-white">MediSlot</span>
          </Link>
          <h2 className="text-2xl font-bold tracking-tight text-white">Sign In to Your Account</h2>
          <p className="mt-1 text-xs text-slate-400">
            Access your appointments, medical queue tracker, and clinical schedule.
          </p>
        </div>

        {/* Quick Demo Login Cards */}
        <div className="glass-panel p-3.5 rounded-2xl border border-indigo-900/40 bg-indigo-950/20">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-300 mb-2.5">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <span>Instant Demo Logins (One-Click)</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => handleQuickLogin("patient")}
              disabled={submitting}
              className="py-2 px-2 text-center rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-teal-500/30 text-teal-300 text-xs font-semibold transition-all hover:scale-[1.02]"
            >
              <span className="block text-[11px] font-bold">Patient</span>
              <span className="text-[9px] text-slate-400">patient1</span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin("doctor")}
              disabled={submitting}
              className="py-2 px-2 text-center rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-blue-500/30 text-blue-300 text-xs font-semibold transition-all hover:scale-[1.02]"
            >
              <span className="block text-[11px] font-bold">Doctor</span>
              <span className="text-[9px] text-slate-400">Dr. Rajesh</span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin("admin")}
              disabled={submitting}
              className="py-2 px-2 text-center rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-purple-500/30 text-purple-300 text-xs font-semibold transition-all hover:scale-[1.02]"
            >
              <span className="block text-[11px] font-bold">Hospital</span>
              <span className="text-[9px] text-slate-400">Admin</span>
            </button>
          </div>
        </div>

        {/* Standard Login Form */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 shadow-2xl">
          {error && (
            <div className="mb-5 flex items-center gap-2 rounded-xl bg-rose-950/40 border border-rose-800/60 p-3 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Mail className="h-4 w-4 text-slate-500" />
                </div>
                <input
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl bg-slate-950/80 border border-slate-800 pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Lock className="h-4 w-4 text-slate-500" />
                </div>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl bg-slate-950/80 border border-slate-800 pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold text-sm hover:opacity-95 shadow-lg shadow-teal-500/20 transition-all flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
            >
              <span>{submitting ? "Signing in..." : "Sign In"}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-400">
            Don't have an account?{" "}
            <Link href="/auth/register" className="font-semibold text-teal-400 hover:text-teal-300 underline">
              Register as a Patient
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
