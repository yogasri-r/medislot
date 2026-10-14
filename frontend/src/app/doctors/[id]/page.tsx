"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  api,
  Doctor,
  SmartSlot,
  SmartSlotsResponse
} from "@/lib/api";
import { formatCurrency, formatDateReadable } from "@/lib/utils";
import { SuggestedSlotBadge } from "@/components/SuggestedSlotBadge";
import {
  Stethoscope,
  Building2,
  MapPin,
  Star,
  Clock,
  Sparkles,
  ShieldCheck,
  Calendar,
  Languages,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  User,
  Users
} from "lucide-react";

export default function DoctorProfilePage() {
  return (
    <React.Suspense fallback={
      <div className="py-24 text-center text-xs text-slate-400 flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
        <span>Loading physician profile, credentials, and schedule...</span>
      </div>
    }>
      <DoctorProfileContent />
    </React.Suspense>
  );
}

function DoctorProfileContent() {
  const params = useParams();
  const router = useRouter();
  const doctorId = params.id as string;

  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [smartSlotsData, setSmartSlotsData] = useState<SmartSlotsResponse | null>(null);
  const [selectedHospitalId, setSelectedHospitalId] = useState<string>("");
  const [selectedDate, setSelectedDate] = useState<string>("2026-10-15");
  const [availableDates, setAvailableDates] = useState<{ dateStr: string; label: string; day: string }[]>([]);

  const [loadingDoctor, setLoadingDoctor] = useState(true);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Generate next 6 dates on client
    const dates: { dateStr: string; label: string; day: string }[] = [];
    const curr = new Date();
    for (let i = 1; dates.length < 6; i++) {
      const temp = new Date();
      temp.setDate(curr.getDate() + i);
      if (temp.getDay() === 0) continue; // skip Sunday
      const iso = temp.toISOString().split("T")[0];
      const isTomorrow = i === 1;
      dates.push({
        dateStr: iso,
        label: isTomorrow ? "Tomorrow" : temp.toLocaleDateString("en-IN", { weekday: "short" }),
        day: temp.toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
      });
    }
    setAvailableDates(dates);
    if (dates.length > 0) {
      setSelectedDate(dates[0].dateStr);
    }
  }, []);

  // Load doctor details
  useEffect(() => {
    if (!doctorId) return;
    setLoadingDoctor(true);
    api.getDoctorById(doctorId)
      .then((doc) => {
        setDoctor(doc);
        const primary = doc.hospitals.find((h) => h.is_primary) || doc.hospitals[0];
        if (primary) setSelectedHospitalId(primary.hospital_id);
      })
      .catch((err) => setError(err.message || "Failed to load doctor profile"))
      .finally(() => setLoadingDoctor(false));
  }, [doctorId]);

  // Load smart slots when doctor, date, or hospital changes
  useEffect(() => {
    if (!doctorId || !selectedDate) return;
    setLoadingSlots(true);
    api.getSmartSlots(doctorId, selectedDate, selectedHospitalId || undefined)
      .then((data) => setSmartSlotsData(data))
      .catch((err) => console.error("Could not fetch smart slots:", err))
      .finally(() => setLoadingSlots(false));
  }, [doctorId, selectedDate, selectedHospitalId]);

  if (loadingDoctor) {
    return (
      <div className="py-24 text-center text-xs text-slate-400 flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
        <span>Loading physician profile, credentials, and schedule...</span>
      </div>
    );
  }

  if (error || !doctor) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-16 text-center">
        <div className="rounded-2xl border border-rose-900/60 bg-rose-950/20 p-8 text-rose-300">
          <AlertCircle className="h-8 w-8 mx-auto mb-2 text-rose-400" />
          <h2 className="text-base font-bold text-white">Physician Not Found</h2>
          <p className="text-xs text-slate-400 mt-1">{error || "The requested doctor could not be located."}</p>
          <Link href="/search" className="mt-4 inline-block text-xs font-semibold text-teal-400 underline">
            Return to Doctor Search
          </Link>
        </div>
      </div>
    );
  }

  const primaryHospital = doctor.hospitals.find((h) => h.is_primary) || doctor.hospitals[0];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Doctor Header Card */}
      <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-slate-800 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row gap-6 items-start justify-between">
          <div className="space-y-4 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="rounded-full bg-teal-500/15 px-3 py-1 text-xs font-bold text-teal-300 border border-teal-500/30">
                {doctor.specialty}
              </span>
              {doctor.is_verified && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-300 border border-emerald-500/30">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  Verified Medical Practitioner
                </span>
              )}
              <span className="text-xs text-slate-500">Reg: {doctor.license_number}</span>
            </div>

            <div>
              <h1 className="text-2xl sm:text-3xl font-black text-white">
                Dr. {doctor.user.full_name}
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 font-medium">
                {doctor.qualification} • {doctor.experience_years} Years Clinical Experience
              </p>
            </div>

            {/* Doctor Bio */}
            {doctor.bio && (
              <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
                {doctor.bio}
              </p>
            )}

            {/* Key Clinical Badges */}
            <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap pt-2">
              <span className="flex items-center gap-1 text-amber-300 font-bold">
                <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                {doctor.rating_avg.toFixed(1)}
                <span className="text-slate-500 font-normal">({doctor.rating_count} verified ratings)</span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <Languages className="h-4 w-4 text-slate-400" />
                Spoken: <strong className="text-white font-medium">{doctor.languages_spoken.join(", ")}</strong>
              </span>
            </div>
          </div>

          {/* Hospital Affiliations Pill */}
          <div className="w-full md:w-auto min-w-[260px] rounded-2xl bg-slate-950/80 p-5 border border-slate-800 space-y-3">
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">
              Consultation Fee
            </span>
            <p className="text-3xl font-black text-white">
              {formatCurrency(doctor.default_consultation_fee)}
            </p>

            <div className="pt-2 border-t border-slate-800/80 space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 block">Practicing At:</span>
              {doctor.hospitals.map((aff) => (
                <button
                  key={aff.id}
                  onClick={() => setSelectedHospitalId(aff.hospital_id)}
                  className={`w-full text-left p-2 rounded-xl text-xs border transition-all ${
                    selectedHospitalId === aff.hospital_id
                      ? "bg-teal-500/15 border-teal-500/40 text-teal-200"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:text-white"
                  }`}
                >
                  <div className="font-semibold">{aff.hospital_name}</div>
                  <div className="text-[10px] text-slate-500 flex items-center justify-between mt-0.5">
                    <span>{aff.hospital_city} {aff.room_number ? `• Room ${aff.room_number}` : ""}</span>
                    {aff.is_primary && <span className="text-teal-400 font-bold">Primary</span>}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Smart Slot Picker */}
      <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-400 mb-1">
              <Sparkles className="h-4 w-4" />
              <span>Smart Slot Recommendation Active</span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Select Outpatient Consultation Slot
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Top 3 slots are algorithmically suggested for optimal clinic schedule flow and minimal delay probability.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
              Available
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-teal-400 ring-2 ring-teal-400/30" />
              Suggested
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
              Booked
            </span>
          </div>
        </div>

        {/* Date Selector Tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {availableDates.map((item) => {
            const isSelected = selectedDate === item.dateStr;
            return (
              <button
                key={item.dateStr}
                onClick={() => setSelectedDate(item.dateStr)}
                className={`py-3 px-4 rounded-xl text-center shrink-0 min-w-[105px] border transition-all ${
                  isSelected
                    ? "bg-gradient-to-tr from-teal-500/20 to-emerald-500/20 border-teal-500/60 text-white shadow-lg shadow-teal-500/10"
                    : "bg-slate-900/80 border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <span className={`block text-xs font-semibold ${isSelected ? "text-teal-300" : ""}`}>
                  {item.label}
                </span>
                <span className="block text-sm font-bold mt-0.5">{item.day}</span>
              </button>
            );
          })}
        </div>

        {/* Slots Grid */}
        <div className="pt-2">
          {loadingSlots ? (
            <div className="py-12 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
              <span>Evaluating schedule density and ranking smart slots...</span>
            </div>
          ) : !smartSlotsData || smartSlotsData.all_slots.length === 0 ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-400">
              <p className="text-sm font-semibold text-white mb-1">No slots scheduled for this date</p>
              <p>The physician may be on leave or outpatient shift has ended. Try selecting another date above.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Highlighted Top 3 Suggested Slots Section */}
              {smartSlotsData.suggested_slots.length > 0 && (
                <div className="rounded-2xl bg-gradient-to-r from-teal-950/30 via-slate-900/60 to-emerald-950/30 border border-teal-500/30 p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-teal-300 flex items-center gap-1.5 uppercase tracking-wider">
                      <Sparkles className="h-4 w-4 text-teal-400" />
                      Top Recommended Consultation Times
                    </span>
                    <span className="text-[11px] text-slate-400">Low clinic delay risk</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {smartSlotsData.suggested_slots.map((slot) => (
                      <Link
                        key={slot.id}
                        href={`/booking/${slot.id}`}
                        className="glass-panel p-4 rounded-xl border border-teal-500/50 hover:border-teal-400 hover:scale-[1.02] transition-all bg-slate-900/90 text-left flex flex-col justify-between group shadow-md shadow-teal-500/10"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-lg font-black text-white group-hover:text-teal-300 transition-colors">
                              {slot.slot_start_ist}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-500/20 text-teal-300 border border-teal-500/40">
                              Top Pick
                            </span>
                          </div>
                          <p className="text-[11px] text-teal-300/90 font-medium line-clamp-2">
                            {slot.suggestion_reason || "Optimal consultation timing with minimal wait"}
                          </p>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs font-bold text-teal-400">
                          <span>Book Slot</span>
                          <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* All Slots Grid */}
              <div>
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                  All Scheduled Slots ({formatDateReadable(selectedDate)})
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
                  {smartSlotsData.all_slots.map((slot) => {
                    const isAvailable = slot.status === "available";
                    const isSuggested = slot.is_suggested;

                    if (!isAvailable) {
                      return (
                        <div
                          key={slot.id}
                          className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 text-center text-slate-600 cursor-not-allowed select-none"
                        >
                          <span className="text-sm font-semibold line-through block">{slot.slot_start_ist}</span>
                          <span className="text-[10px] uppercase font-bold text-slate-700">Booked</span>
                        </div>
                      );
                    }

                    return (
                      <Link
                        key={slot.id}
                        href={`/booking/${slot.id}`}
                        className={`p-3 rounded-xl text-center border transition-all hover:scale-[1.03] flex flex-col justify-center ${
                          isSuggested
                            ? "bg-teal-500/15 border-teal-500/60 text-white shadow-sm shadow-teal-500/20"
                            : "bg-slate-900/90 border-slate-800 text-slate-200 hover:border-teal-500/40 hover:text-white"
                        }`}
                      >
                        <span className="text-sm font-bold block">{slot.slot_start_ist}</span>
                        {isSuggested ? (
                          <span className="text-[10px] font-bold text-teal-300 mt-0.5 flex items-center justify-center gap-0.5">
                            <Sparkles className="h-2.5 w-2.5" />
                            Suggested
                          </span>
                        ) : (
                          <span className="text-[10px] text-emerald-400 mt-0.5">Available</span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
