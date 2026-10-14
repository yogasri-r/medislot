"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search,
  Sparkles,
  Clock,
  ShieldCheck,
  Activity,
  Calendar,
  MapPin,
  Star,
  Users,
  ArrowRight,
  HeartPulse,
  Stethoscope,
  Building2,
  CheckCircle2
} from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [specialty, setSpecialty] = useState("");
  const [city, setCity] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (specialty) params.append("specialty", specialty);
    if (city) params.append("city", city);
    router.push(`/search?${params.toString()}`);
  };

  const hospitals = [
    {
      name: "Kovai Apex Medical Center",
      city: "Coimbatore",
      address: "142 Avinashi Road, Peelamedu",
      doctors: 12,
      specialties: "Cardiology, Orthopedics, Neurology, Pediatrics",
      color: "from-teal-500/20 to-emerald-500/10"
    },
    {
      name: "Cauvery Valley General Hospital",
      city: "Erode",
      address: "88 Perundurai Main Road",
      doctors: 10,
      specialties: "General Medicine, Dermatology, Cardiology",
      color: "from-blue-500/20 to-indigo-500/10"
    },
    {
      name: "Kongu Metro Healthcare",
      city: "Tiruppur",
      address: "55 Palladam Road, Thennampalayam",
      doctors: 10,
      specialties: "Pediatrics, ENT, Gynecology, Orthopedics",
      color: "from-indigo-500/20 to-purple-500/10"
    },
    {
      name: "Amaravathi Care Hospital",
      city: "Dharapuram",
      address: "22 Kangeyam Bypass Road",
      doctors: 8,
      specialties: "General Medicine, Gynecology, Dermatology",
      color: "from-amber-500/20 to-emerald-500/10"
    }
  ];

  return (
    <div className="flex flex-col gap-16 pb-20">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 md:pt-20 md:pb-28">
        {/* Glow ambient background lights */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[350px] bg-teal-500/15 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute top-1/3 left-1/3 w-[400px] h-[300px] bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-900/90 border border-teal-500/30 px-4 py-1.5 text-xs font-semibold text-teal-300 shadow-xl shadow-teal-500/5 mb-6">
            <Sparkles className="h-3.5 w-3.5 text-teal-400" />
            <span>Next-Generation Outpatient Scheduling</span>
            <span className="text-slate-500">•</span>
            <span className="text-slate-300">Western Tamil Nadu Network</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight text-white max-w-4xl mx-auto leading-[1.1]">
            Right doctor. Right slot.{" "}
            <span className="bg-gradient-to-r from-teal-400 via-emerald-400 to-indigo-400 bg-clip-text text-transparent">
              Less waiting.
            </span>
          </h1>

          <p className="mt-6 text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Eliminate outpatient waiting room congestion with AI-recommended physicians, schedule gap-filling smart slots, and real-time live clinic queue estimation.
          </p>

          {/* Quick Search Widget */}
          <div className="mt-10 max-w-3xl mx-auto">
            <form
              onSubmit={handleSearch}
              className="glass-panel p-2.5 rounded-2xl shadow-2xl flex flex-col sm:flex-row gap-2 border border-slate-700/80"
            >
              <div className="flex-1 flex items-center gap-3 px-3 py-2 bg-slate-950/60 rounded-xl border border-slate-800">
                <Stethoscope className="h-5 w-5 text-teal-400 shrink-0" />
                <input
                  type="text"
                  placeholder="Specialty (e.g., Cardiology, Dermatology)"
                  value={specialty}
                  onChange={(e) => setSpecialty(e.target.value)}
                  className="w-full bg-transparent text-sm text-white placeholder-slate-400 focus:outline-none"
                />
              </div>

              <div className="flex-1 flex items-center gap-3 px-3 py-2 bg-slate-950/60 rounded-xl border border-slate-800">
                <MapPin className="h-5 w-5 text-indigo-400 shrink-0" />
                <select
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full bg-transparent text-sm text-white focus:outline-none [&>option]:bg-slate-900"
                >
                  <option value="">All Western TN Cities</option>
                  <option value="Coimbatore">Coimbatore</option>
                  <option value="Erode">Erode</option>
                  <option value="Tiruppur">Tiruppur</option>
                  <option value="Dharapuram">Dharapuram</option>
                </select>
              </div>

              <button
                type="submit"
                className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold text-sm hover:opacity-95 shadow-lg shadow-teal-500/20 transition-all flex items-center justify-center gap-2 shrink-0"
              >
                <Search className="h-4 w-4" />
                <span>Find Doctors</span>
              </button>
            </form>

            <div className="flex flex-wrap items-center justify-center gap-2 mt-4 text-xs text-slate-400">
              <span className="font-medium text-slate-500">Popular:</span>
              {["Cardiology", "Dermatology", "Pediatrics", "Orthopedics", "General Medicine"].map((spec) => (
                <button
                  key={spec}
                  onClick={() => router.push(`/search?specialty=${spec}`)}
                  className="px-2.5 py-1 rounded-full bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
                >
                  {spec}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 3 Pillars Value Props */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Designed to End Outpatient Chaos
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            MediSlot solves the three primary failure modes of outpatient clinic scheduling.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="glass-panel p-6 rounded-2xl glass-card-hover border border-slate-800">
            <div className="h-12 w-12 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 mb-5">
              <Sparkles className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Smart Slot Gap-Filling</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Our recommendation engine identifies the <strong>Top 3 Suggested Slots</strong> that pack doctor consultation blocks, minimize clinic delay accumulation, and respect patient circadian preferences.
            </p>
            <div className="mt-4 flex items-center gap-2 text-xs font-semibold text-teal-400">
              <span>View suggested slot badges</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </div>

          {/* Card 2 */}
          <div className="glass-panel p-6 rounded-2xl glass-card-hover border border-slate-800">
            <div className="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-5">
              <Clock className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Live Day-Of Queue Tracking</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Never sit idly in crowded hospital waiting halls. Real-time queue calculations track patients ahead, physician delays, and dynamically advise staggered arrival windows.
            </p>
            <div className="mt-4 flex items-center gap-2 text-xs font-semibold text-indigo-400">
              <span>Dynamic wait estimates</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </div>

          {/* Card 3 */}
          <div className="glass-panel p-6 rounded-2xl glass-card-hover border border-slate-800">
            <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-5">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">ML No-Show & Wait Predictions</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Trained gradient boosting pipelines predict consultation durations with a 39.3% error reduction, and proactively dispatch targeted attendance confirmations to prevent vacant clinical slots.
            </p>
            <div className="mt-4 flex items-center gap-2 text-xs font-semibold text-emerald-400">
              <span>Machine learning validated</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </div>
        </div>
      </section>

      {/* Network Hospitals Section */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <span className="text-xs font-bold text-teal-400 uppercase tracking-wider">Multi-Hospital Network</span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
              Western Tamil Nadu Healthcare Clusters
            </h2>
          </div>
          <Link
            href="/search"
            className="flex items-center gap-1.5 text-xs font-semibold text-teal-400 hover:text-teal-300 transition-colors"
          >
            <span>Explore All 40 Verified Doctors</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {hospitals.map((h, idx) => (
            <div
              key={h.name}
              className={`glass-panel p-5 rounded-2xl border border-slate-800 relative overflow-hidden bg-gradient-to-br ${h.color} hover:border-slate-700 transition-all flex flex-col justify-between`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-950/80 text-teal-300 border border-teal-500/30">
                    <MapPin className="h-3 w-3" />
                    {h.city}
                  </span>
                  <span className="text-[11px] text-slate-400">{h.doctors} Doctors</span>
                </div>

                <h3 className="text-base font-bold text-white mb-1.5 leading-snug">{h.name}</h3>
                <p className="text-xs text-slate-400 mb-3">{h.address}</p>
                <div className="text-[11px] text-slate-400 bg-slate-950/50 p-2.5 rounded-xl border border-slate-800/80">
                  <strong className="text-slate-300 font-semibold block mb-0.5">Key Specialties:</strong>
                  {h.specialties}
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800/60">
                <Link
                  href={`/search?city=${h.city}`}
                  className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-slate-900/80 hover:bg-slate-800 text-teal-300 border border-slate-700/80 flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>Book at {h.city}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Call To Action Banner */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="rounded-3xl bg-gradient-to-r from-teal-950/80 via-slate-900 to-indigo-950/80 border border-teal-500/30 p-8 sm:p-12 text-center relative overflow-hidden shadow-2xl">
          <div className="relative max-w-2xl mx-auto space-y-4">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Ready for a Seamless Healthcare Experience?
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              Book your outpatient consultation in seconds, view suggested slots, and track your queue live from anywhere.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-3">
              <Link
                href="/search"
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold text-sm hover:opacity-95 shadow-xl shadow-teal-500/25 transition-all"
              >
                Search Available Doctors
              </Link>
              <Link
                href="/auth/register"
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-sm border border-slate-700 transition-colors"
              >
                Create Free Patient Account
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
