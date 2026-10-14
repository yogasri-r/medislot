"use client";

import React from "react";
import Link from "next/link";
import { Activity, ShieldAlert, Heart, MapPin, PhoneCall } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-800/80 bg-slate-950 text-slate-400 text-xs mt-auto">
      {/* Emergency Disclaimer Banner */}
      <div className="bg-rose-950/40 border-b border-rose-900/40 py-2.5 px-4 text-center">
        <div className="mx-auto flex max-w-7xl items-center justify-center gap-2 text-rose-300 font-medium">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <span>
            Medical Emergency? If experiencing chest pain, severe breathlessness, or stroke symptoms, immediately dial{" "}
            <strong className="text-white underline font-bold">108</strong> or{" "}
            <strong className="text-white underline font-bold">112</strong>. Do not book outpatient slots for emergency triage.
          </span>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Info */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500 p-1.5 shadow-md">
                <Activity className="h-5 w-5 text-slate-950 stroke-[2.5]" />
              </div>
              <span className="text-base font-bold text-white tracking-tight">MediSlot</span>
            </div>
            <p className="text-slate-400 text-xs leading-relaxed">
              Multi-hospital intelligent healthcare appointment scheduling platform serving Western Tamil Nadu clusters.
            </p>
          </div>

          {/* Network Hospitals */}
          <div>
            <h4 className="text-slate-200 font-semibold mb-2.5 text-xs uppercase tracking-wider">
              Network Hospitals
            </h4>
            <ul className="space-y-1.5 text-slate-400 text-xs">
              <li className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-teal-400 shrink-0" />
                <span>Kovai Apex Medical Center (Coimbatore)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-teal-400 shrink-0" />
                <span>Cauvery Valley General (Erode)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-teal-400 shrink-0" />
                <span>Kongu Metro Healthcare (Tiruppur)</span>
              </li>
              <li className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-teal-400 shrink-0" />
                <span>Amaravathi Care Hospital (Dharapuram)</span>
              </li>
            </ul>
          </div>

          {/* Platform Features */}
          <div>
            <h4 className="text-slate-200 font-semibold mb-2.5 text-xs uppercase tracking-wider">
              Core Capabilities
            </h4>
            <ul className="space-y-1.5 text-slate-400 text-xs">
              <li>• Multi-Factor Doctor Recommendations</li>
              <li>• Schedule Gap-Filling Smart Slots</li>
              <li>• Real-Time Queue & Wait Time Estimator</li>
              <li>• Machine Learning No-Show Risk Alerts</li>
              <li>• Automated Multi-Channel Reminders</li>
            </ul>
          </div>

          {/* Quick Access */}
          <div>
            <h4 className="text-slate-200 font-semibold mb-2.5 text-xs uppercase tracking-wider">
              Quick Links
            </h4>
            <ul className="space-y-1.5 text-slate-400 text-xs">
              <li><Link href="/search" className="hover:text-teal-300">Find Doctors</Link></li>
              <li><Link href="/my-appointments" className="hover:text-teal-300">My Appointments</Link></li>
              <li><Link href="/doctor/dashboard" className="hover:text-teal-300">Doctor Clinical Portal</Link></li>
              <li><Link href="/auth/login" className="hover:text-teal-300">Sign In</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t border-slate-800/60 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-500">
          <p>© 2026 MediSlot Healthcare Platform. All rights reserved.</p>
          <p className="flex items-center gap-1">
            Built with care for streamlined clinical workflows and patient dignity.
          </p>
        </div>
      </div>
    </footer>
  );
}
