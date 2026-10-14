"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  api,
  DoctorRecommendation,
  Hospital
} from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import {
  Search,
  Filter,
  MapPin,
  Star,
  Clock,
  Sparkles,
  Stethoscope,
  Building2,
  Calendar,
  Languages,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle
} from "lucide-react";

export default function SearchPage() {
  return (
    <React.Suspense fallback={
      <div className="py-24 text-center text-xs text-slate-400 flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
        <span>Initializing doctor recommendation engine...</span>
      </div>
    }>
      <SearchContent />
    </React.Suspense>
  );
}

function SearchContent() {
  const searchParams = useSearchParams();

  // Filters
  const [specialty, setSpecialty] = useState(searchParams.get("specialty") || "");
  const [city, setCity] = useState(searchParams.get("city") || "");
  const [hospitalId, setHospitalId] = useState(searchParams.get("hospital_id") || "");
  const [language, setLanguage] = useState("");
  const [gender, setGender] = useState("");
  const [maxFee, setMaxFee] = useState<number>(1000);

  // AI Natural Language Search state
  const [nlQuery, setNlQuery] = useState("");
  const [isParsingNL, setIsParsingNL] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);

  // Data
  const [recommendations, setRecommendations] = useState<DoctorRecommendation[]>([]);
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load hospitals on mount
  useEffect(() => {
    api.getHospitals()
      .then((data) => setHospitals(data))
      .catch((err) => console.error("Could not load hospitals:", err));
  }, []);

  // Fetch doctors
  const fetchDoctors = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRecommendedDoctors({
        specialty: specialty || undefined,
        city: city || undefined,
        hospital_id: hospitalId || undefined,
        language: language || undefined,
        gender: gender || undefined,
        max_fee: maxFee || undefined,
        limit: 20
      });
      setRecommendations(data);
    } catch (err: any) {
      setError(err.message || "Failed to load doctor recommendations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDoctors();
  }, [specialty, city, hospitalId, language, gender, maxFee]);

  const handleNLSearch = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const query = customQuery || nlQuery;
    if (!query.trim()) return;

    setIsParsingNL(true);
    try {
      const res = await api.parseNLSearch(query, city || undefined);
      if (res.filters) {
        if (res.filters.specialty) setSpecialty(res.filters.specialty);
        if (res.filters.city) setCity(res.filters.city);
        if (res.filters.gender) setGender(res.filters.gender);
        if (res.filters.language) setLanguage(res.filters.language);
        if (res.filters.max_fee) setMaxFee(res.filters.max_fee);
        setAiSummary(res.filters.summary);
      }
    } catch (err) {
      console.error("NL parse failed:", err);
    } finally {
      setIsParsingNL(false);
    }
  };

  const specialtiesList = [
    "Cardiology",
    "Orthopedics",
    "Neurology",
    "Pediatrics",
    "General Medicine",
    "Dermatology",
    "ENT",
    "Gynecology"
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 rounded-full bg-teal-500/10 px-3 py-1 text-xs font-semibold text-teal-300 border border-teal-500/20 mb-2">
          <Sparkles className="h-3.5 w-3.5 text-teal-400" />
          Multi-Factor AI Recommendation Engine Active
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Find Top Doctors & Recommended Consultation Slots
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-400">
          Ranked by clinical specialty match, earliest availability, Bayesian verified ratings, and Western Tamil Nadu cluster proximity.
        </p>

        {/* AI Natural Language Search Card */}
        <div className="mt-6 p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/60 border border-teal-500/30 shadow-xl shadow-teal-500/5">
          <form onSubmit={handleNLSearch} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Sparkles className="absolute left-3.5 top-3.5 h-4 w-4 text-teal-400" />
              <input
                type="text"
                value={nlQuery}
                onChange={(e) => setNlQuery(e.target.value)}
                placeholder="Describe what you need in plain English (e.g. 'female dermatologist in Coimbatore under 800 rupees speaking Tamil')..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950/90 border border-slate-700/80 text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-teal-400 transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={isParsingNL || !nlQuery.trim()}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs sm:text-sm transition-all shadow-md shadow-teal-500/20 flex items-center justify-center gap-2 shrink-0"
            >
              <Sparkles className="h-4 w-4" />
              {isParsingNL ? "Analyzing Query..." : "AI Smart Search"}
            </button>
          </form>

          {/* Quick Preset Queries & Active AI Filter Badge */}
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-400 text-[11px]">Try:</span>
            <button
              type="button"
              onClick={() => {
                const q = "female dermatologist in Coimbatore under 800 rupees speaking Tamil";
                setNlQuery(q);
                handleNLSearch(undefined, q);
              }}
              className="px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[11px] border border-slate-700/60 transition-colors"
            >
              👩‍⚕️ Female Dermatologist in Coimbatore
            </button>
            <button
              type="button"
              onClick={() => {
                const q = "orthopedic knee specialist in Tiruppur";
                setNlQuery(q);
                handleNLSearch(undefined, q);
              }}
              className="px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[11px] border border-slate-700/60 transition-colors"
            >
              🦵 Knee specialist in Tiruppur
            </button>
            <button
              type="button"
              onClick={() => {
                const q = "cardiologist in Coimbatore under 1000 rupees";
                setNlQuery(q);
                handleNLSearch(undefined, q);
              }}
              className="px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-[11px] border border-slate-700/60 transition-colors"
            >
              ❤️ Cardiologist under ₹1000
            </button>

            {aiSummary && (
              <div className="ml-auto flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/20 border border-teal-500/40 text-teal-300 text-[11px]">
                <Sparkles className="h-3 w-3 text-teal-300" />
                <span>AI Applied: {aiSummary}</span>
                <button
                  type="button"
                  onClick={() => setAiSummary(null)}
                  className="ml-1 text-teal-200 hover:text-white"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left Filter Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-5 sticky top-20">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-sm font-bold text-white flex items-center gap-2">
                <Filter className="h-4 w-4 text-teal-400" />
                Refine Search
              </span>
              {(specialty || city || hospitalId || language || gender) && (
                <button
                  onClick={() => {
                    setSpecialty("");
                    setCity("");
                    setHospitalId("");
                    setLanguage("");
                    setGender("");
                    setMaxFee(1000);
                  }}
                  className="text-[11px] text-teal-400 hover:underline"
                >
                  Reset
                </button>
              )}
            </div>

            {/* Specialty */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Specialty</label>
              <select
                value={specialty}
                onChange={(e) => setSpecialty(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:border-teal-500 focus:outline-none [&>option]:bg-slate-900"
              >
                <option value="">All Specialties</option>
                {specialtiesList.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* City */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">City / Cluster</label>
              <select
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:border-teal-500 focus:outline-none [&>option]:bg-slate-900"
              >
                <option value="">All Western TN Cities</option>
                <option value="Coimbatore">Coimbatore</option>
                <option value="Erode">Erode</option>
                <option value="Tiruppur">Tiruppur</option>
                <option value="Dharapuram">Dharapuram</option>
              </select>
            </div>

            {/* Hospital Filter */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Hospital Network</label>
              <select
                value={hospitalId}
                onChange={(e) => setHospitalId(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:border-teal-500 focus:outline-none [&>option]:bg-slate-900"
              >
                <option value="">All 4 Hospitals</option>
                {hospitals.map((h) => (
                  <option key={h.id} value={h.id}>{h.name} ({h.city})</option>
                ))}
              </select>
            </div>

            {/* Language */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Spoken Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-white focus:border-teal-500 focus:outline-none [&>option]:bg-slate-900"
              >
                <option value="">Any Language</option>
                <option value="Tamil">Tamil</option>
                <option value="English">English</option>
                <option value="Malayalam">Malayalam</option>
                <option value="Telugu">Telugu</option>
              </select>
            </div>

            {/* Gender */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Doctor Gender</label>
              <div className="grid grid-cols-3 gap-1.5">
                {["", "Female", "Male"].map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGender(g)}
                    className={`py-1.5 px-2 text-center rounded-lg text-xs font-medium border transition-colors ${
                      gender === g
                        ? "bg-teal-500/20 text-teal-300 border-teal-500/40"
                        : "bg-slate-950 text-slate-400 border-slate-800 hover:text-white"
                    }`}
                  >
                    {g === "" ? "Any" : g}
                  </button>
                ))}
              </div>
            </div>

            {/* Max Fee Slider */}
            <div>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="font-semibold text-slate-300">Max Fee:</span>
                <span className="font-bold text-teal-400">{formatCurrency(maxFee)}</span>
              </div>
              <input
                type="range"
                min="300"
                max="1500"
                step="50"
                value={maxFee}
                onChange={(e) => setMaxFee(Number(e.target.value))}
                className="w-full accent-teal-500 bg-slate-950 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                <span>₹300</span>
                <span>₹1,500</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Doctor Cards Grid */}
        <div className="lg:col-span-3 space-y-4">
          {/* Status Bar */}
          <div className="flex items-center justify-between text-xs text-slate-400 pb-2">
            <span>Showing <strong className="text-white">{recommendations.length}</strong> verified doctors</span>
            <span className="text-teal-400 font-medium">Sorted by composite match score</span>
          </div>

          {loading && (
            <div className="py-16 text-center text-slate-400 text-xs flex flex-col items-center gap-3">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
              <span>Matching physicians and evaluating upcoming slot availability...</span>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-900/60 bg-rose-950/30 p-4 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && recommendations.length === 0 && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center text-xs text-slate-400">
              <p className="text-sm font-semibold text-white mb-1">No doctors match your exact filter criteria</p>
              <p>Try broadening your specialty, location, or maximum consultation fee ceiling.</p>
            </div>
          )}

          {!loading && recommendations.map((rec) => {
            const doc = rec.doctor;
            const primaryHosp = doc.hospitals.find((h) => h.is_primary) || doc.hospitals[0];

            return (
              <div
                key={doc.id}
                className="glass-panel p-5 sm:p-6 rounded-2xl border border-slate-800 glass-card-hover flex flex-col md:flex-row justify-between gap-6"
              >
                {/* Doctor Main Information */}
                <div className="space-y-3 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-lg font-bold text-white hover:text-teal-300 transition-colors">
                          <Link href={`/doctors/${doc.id}`}>
                            Dr. {doc.user.full_name}
                          </Link>
                        </h3>
                        {doc.is_verified && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-teal-500/10 px-2 py-0.5 text-[10px] font-bold text-teal-300 border border-teal-500/30">
                            <ShieldCheck className="h-3 w-3 text-teal-400" />
                            Verified
                          </span>
                        )}
                        <span className="rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-[10px] font-bold text-indigo-300 border border-indigo-500/30">
                          {doc.specialty}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{doc.qualification}</p>
                    </div>

                    {/* Composite Match Badge */}
                    <div className="text-right shrink-0">
                      <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Match Score</span>
                      <span className="text-sm font-black text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded-lg border border-teal-500/30">
                        {Math.round(rec.composite_score * 100)}%
                      </span>
                    </div>
                  </div>

                  {/* Hospital & Location */}
                  {primaryHosp && (
                    <div className="flex items-center gap-4 text-xs text-slate-300 flex-wrap">
                      <span className="flex items-center gap-1.5 font-medium">
                        <Building2 className="h-3.5 w-3.5 text-teal-400 shrink-0" />
                        {primaryHosp.hospital_name}
                      </span>
                      <span className="flex items-center gap-1 text-slate-400">
                        <MapPin className="h-3 w-3 text-indigo-400 shrink-0" />
                        {primaryHosp.hospital_city}
                      </span>
                    </div>
                  )}

                  {/* Rating, Experience, Languages */}
                  <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap pt-1">
                    <span className="flex items-center gap-1 font-semibold text-amber-300">
                      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                      {doc.rating_avg.toFixed(1)}
                      <span className="text-slate-500 font-normal">({doc.rating_count} reviews)</span>
                    </span>
                    <span>•</span>
                    <span>{doc.experience_years} years clinical exp</span>
                    <span>•</span>
                    <span className="flex items-center gap-1 text-slate-300">
                      <Languages className="h-3.5 w-3.5 text-slate-400" />
                      {doc.languages_spoken.join(", ")}
                    </span>
                  </div>

                  {/* AI Explanation Pill */}
                  <div className="rounded-xl bg-slate-950/60 p-2.5 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
                    <Sparkles className="h-3.5 w-3.5 text-teal-400 shrink-0" />
                    <span className="italic">{rec.explanation}</span>
                  </div>
                </div>

                {/* Right Action / Booking Box */}
                <div className="shrink-0 flex flex-col justify-between border-t md:border-t-0 md:border-l border-slate-800 pt-4 md:pt-0 md:pl-6 min-w-[200px]">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Consultation Fee</span>
                    <p className="text-2xl font-black text-white mt-0.5">
                      {formatCurrency(doc.default_consultation_fee)}
                    </p>
                    <span className="text-[10px] text-slate-500">Includes outpatient OPD ticket</span>
                  </div>

                  <div className="space-y-2 mt-4">
                    {rec.earliest_available_slot_ist ? (
                      <div className="rounded-lg bg-emerald-950/40 border border-emerald-800/60 px-2.5 py-1.5 text-center text-[11px] text-emerald-300 font-medium">
                        <Clock className="h-3 w-3 inline mr-1 text-emerald-400" />
                        Next: {rec.earliest_available_slot_ist}
                      </div>
                    ) : (
                      <div className="rounded-lg bg-amber-950/40 border border-amber-800/60 px-2.5 py-1.5 text-center text-[11px] text-amber-300 font-medium">
                        Waitlist Available
                      </div>
                    )}

                    <Link
                      href={`/doctors/${doc.id}`}
                      className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold text-xs hover:opacity-95 shadow-md shadow-teal-500/20 transition-all flex items-center justify-center gap-1.5 text-center"
                    >
                      <span>View Suggested Slots</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
