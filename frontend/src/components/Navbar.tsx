"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  Activity,
  Calendar,
  Search,
  User,
  LogOut,
  Stethoscope,
  ChevronDown,
  Sparkles,
  ShieldAlert,
  Hospital
} from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const { user, logout, loginAsPreset } = useAuth();
  const [demoMenuOpen, setDemoMenuOpen] = useState(false);

  const navLinks = [
    { href: "/search", label: "Find Doctors", icon: Search },
    { href: "/my-appointments", label: "My Appointments", icon: Calendar },
    ...(user?.role === "hospital_admin"
      ? [{ href: "/admin/dashboard", label: "Hospital Ops", icon: Hospital }]
      : user?.role === "super_admin"
      ? [{ href: "/super-admin/dashboard", label: "Super Admin", icon: ShieldAlert }]
      : [{ href: "/doctor/dashboard", label: "Doctor Portal", icon: Stethoscope }]),
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-teal-500 to-emerald-400 p-2 shadow-lg shadow-teal-500/20 group-hover:scale-105 transition-transform">
            <Activity className="h-6 w-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
              MediSlot
              <span className="rounded-full bg-teal-500/20 px-2 py-0.5 text-[10px] font-semibold text-teal-300 border border-teal-500/30">
                AI Powered
              </span>
            </span>
            <p className="text-[11px] font-medium text-slate-400 hidden sm:block">
              Right doctor. Right slot. Less waiting.
            </p>
          </div>
        </Link>

        {/* Center Nav Links */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800/60">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href || pathname?.startsWith(link.href + "/");
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-teal-500/15 text-teal-300 border border-teal-500/30"
                    : "text-slate-300 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-teal-400" : "text-slate-400"}`} />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right Action Menu */}
        <div className="flex items-center gap-2.5">
          {/* Quick Demo Role Switcher for instant evaluator login */}
          <div className="relative">
            <button
              onClick={() => setDemoMenuOpen(!demoMenuOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-800/60 hover:bg-indigo-900/40 transition-colors"
              title="Quick Demo Role Switcher"
            >
              <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
              <span className="hidden sm:inline">Demo Persona</span>
              <ChevronDown className="h-3 w-3" />
            </button>

            {demoMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 rounded-xl bg-slate-900 border border-slate-800 p-2 shadow-2xl z-50 text-xs">
                <p className="px-2 py-1 font-semibold text-slate-400 uppercase tracking-wider text-[10px]">
                  Switch Quick Demo Role
                </p>
                <button
                  onClick={() => { loginAsPreset("patient"); setDemoMenuOpen(false); }}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>Patient (patient1)</span>
                  <span className="text-[10px] bg-teal-500/20 text-teal-300 px-1.5 py-0.5 rounded">Patient</span>
                </button>
                <button
                  onClick={() => { loginAsPreset("doctor"); setDemoMenuOpen(false); }}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>Dr. Rajesh (doctor1)</span>
                  <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded">Doctor</span>
                </button>
                <button
                  onClick={() => { loginAsPreset("admin"); setDemoMenuOpen(false); }}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>Coimbatore Admin</span>
                  <span className="text-[10px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Hosp Admin</span>
                </button>
                <button
                  onClick={() => { loginAsPreset("super_admin"); setDemoMenuOpen(false); }}
                  className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-200 flex items-center justify-between"
                >
                  <span>Network Super Admin</span>
                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded">Super Admin</span>
                </button>
              </div>
            )}
          </div>

          {/* User Profile or Login */}
          {user ? (
            <div className="flex items-center gap-2 bg-slate-900/80 pl-3 pr-1.5 py-1 rounded-xl border border-slate-800 text-xs">
              <div className="flex flex-col text-right">
                <span className="font-semibold text-slate-200 truncate max-w-[120px]">
                  {user.full_name}
                </span>
                <span className="text-[10px] text-teal-400 uppercase tracking-wider capitalize">
                  {user.role.replace("_", " ")}
                </span>
              </div>
              <button
                onClick={logout}
                title="Logout"
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition-colors"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/auth/login"
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/auth/register"
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold hover:opacity-95 shadow-md shadow-teal-500/20 transition-all"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
