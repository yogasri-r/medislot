"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatCurrency, formatDateReadable } from "@/lib/utils";
import {
  Calendar,
  Clock,
  Building2,
  Stethoscope,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  User,
  Sparkles,
  FileText
} from "lucide-react";

export default function BookingPage() {
  return (
    <React.Suspense fallback={
      <div className="py-24 text-center text-xs text-slate-400 flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
        <span>Loading reservation details...</span>
      </div>
    }>
      <BookingContent />
    </React.Suspense>
  );
}

function BookingContent() {
  const params = useParams();
  const router = useRouter();
  const slotId = params.slot_id as string;
  const { user, loginAsPreset } = useAuth();

  const [slot, setSlot] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [appointmentType, setAppointmentType] = useState<"new_patient" | "follow_up">("new_patient");
  const [notes, setNotes] = useState("");
  const [confirmedBooking, setConfirmedBooking] = useState<any>(null);

  useEffect(() => {
    if (!slotId) return;
    setLoading(true);
    api.getSlotById(slotId)
      .then((data) => setSlot(data))
      .catch((err) => setError(err.message || "Failed to load slot details"))
      .finally(() => setLoading(false));
  }, [slotId]);

  const handleBook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) {
      setError("Please sign in or use a demo persona below to confirm booking.");
      return;
    }

    setBooking(true);
    setError(null);
    try {
      const res = await api.bookAppointment({
        slot_id: slotId,
        appointment_type: appointmentType,
        notes: notes || undefined
      });
      setConfirmedBooking(res);
    } catch (err: any) {
      setError(err.message || "Booking failed. The slot may have been claimed by another patient.");
    } finally {
      setBooking(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-xs text-slate-400 flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
        <span>Loading reservation details...</span>
      </div>
    );
  }

  if (!slot && !confirmedBooking) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <div className="rounded-2xl border border-rose-900/60 bg-rose-950/20 p-8 text-rose-300">
          <AlertCircle className="h-8 w-8 mx-auto mb-2 text-rose-400" />
          <h2 className="text-base font-bold text-white">Slot Unavailable</h2>
          <p className="text-xs text-slate-400 mt-1">{error || "This consultation slot could not be found."}</p>
          <Link href="/search" className="mt-4 inline-block text-xs font-semibold text-teal-400 underline">
            Find Another Doctor
          </Link>
        </div>
      </div>
    );
  }

  // Success Confirmation Screen
  if (confirmedBooking) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
        <div className="glass-panel p-8 rounded-3xl border border-emerald-500/40 bg-gradient-to-b from-slate-900 to-slate-950 shadow-2xl text-center space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-lg shadow-emerald-500/10">
            <CheckCircle2 className="h-8 w-8" />
          </div>

          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
              Appointment Confirmed
            </span>
            <h1 className="text-2xl sm:text-3xl font-black text-white mt-1">
              Reservation Successfully Booked
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Reference Token: <strong className="text-white font-mono">{confirmedBooking.appointment_number}</strong>
            </p>
          </div>

          {/* Clinical Ticket Card */}
          <div className="rounded-2xl bg-slate-950/80 p-5 border border-slate-800 text-left space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500">Patient</span>
                <p className="text-sm font-bold text-white">{user?.full_name || "Patient"}</p>
              </div>
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-slate-500">Type</span>
                <p className="text-xs font-bold text-teal-400 capitalize">{appointmentType.replace("_", " ")}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500">Scheduled Time</span>
                <p className="font-semibold text-slate-200">{slot?.slot_start_ist || "Slot Time"}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-slate-500">Consultation Fee</span>
                <p className="font-semibold text-slate-200">{formatCurrency(slot?.doctor?.default_consultation_fee || 500)}</p>
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-teal-950/30 border border-teal-800/40 p-3.5 text-xs text-teal-300 text-left">
            <Sparkles className="h-4 w-4 inline mr-1 text-teal-400" />
            A booking confirmation email has been dispatched with one-click response links.
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Link
              href="/my-appointments"
              className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold text-xs hover:opacity-95 shadow-md shadow-teal-500/20 text-center flex items-center justify-center gap-1.5"
            >
              <span>View in My Appointments (Live Queue)</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/search"
              className="py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold text-center"
            >
              Book Another
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const doc = slot.doctor;
  const hosp = slot.hospital;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          Review & Confirm Outpatient Booking
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Review your physician reservation and specify your visit reason.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left Form */}
        <div className="md:col-span-2 space-y-6">
          {error && (
            <div className="rounded-xl border border-rose-900/60 bg-rose-950/30 p-4 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {/* User Sign-In Notice if guest */}
          {!user && (
            <div className="glass-panel p-4 rounded-2xl border border-indigo-900/60 bg-indigo-950/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                  <User className="h-4 w-4" />
                  Sign in required to confirm appointment
                </span>
              </div>
              <p className="text-xs text-slate-400">
                You can sign in with your patient account or click below for an instant demo login:
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => loginAsPreset("patient")}
                  className="py-1.5 px-3 rounded-lg bg-teal-500/20 text-teal-300 border border-teal-500/40 text-xs font-bold hover:bg-teal-500/30 transition-colors"
                >
                  ⚡ One-Click Login as Patient (patient1)
                </button>
                <Link
                  href="/auth/login"
                  className="py-1.5 px-3 rounded-lg bg-slate-900 text-slate-300 border border-slate-700 text-xs font-medium hover:text-white"
                >
                  Sign In
                </Link>
              </div>
            </div>
          )}

          {/* Booking Form */}
          <form onSubmit={handleBook} className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
            {/* Appointment Type */}
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                Consultation Type
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                    appointmentType === "new_patient"
                      ? "bg-teal-500/15 border-teal-500/50 text-white"
                      : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs">New Patient</span>
                    <input
                      type="radio"
                      name="appointmentType"
                      value="new_patient"
                      checked={appointmentType === "new_patient"}
                      onChange={() => setAppointmentType("new_patient")}
                      className="accent-teal-500"
                    />
                  </div>
                  <span className="text-[11px] text-slate-400 leading-snug">
                    First consultation for this medical symptom (~25 mins)
                  </span>
                </label>

                <label
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                    appointmentType === "follow_up"
                      ? "bg-teal-500/15 border-teal-500/50 text-white"
                      : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs">Follow-Up Review</span>
                    <input
                      type="radio"
                      name="appointmentType"
                      value="follow_up"
                      checked={appointmentType === "follow_up"}
                      onChange={() => setAppointmentType("follow_up")}
                      className="accent-teal-500"
                    />
                  </div>
                  <span className="text-[11px] text-slate-400 leading-snug">
                    Report review or prescription renewal (~15 mins)
                  </span>
                </label>
              </div>
            </div>

            {/* Notes / Reason for Visit */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center justify-between">
                <span>Reason for Visit & Symptoms (Optional)</span>
                <span className="text-[10px] text-slate-500">Shared privately with doctor</span>
              </label>
              <textarea
                rows={3}
                placeholder="Briefly describe your symptoms or concern (e.g. persistent cough for 4 days, mild fever)..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full rounded-xl bg-slate-950/80 border border-slate-800 p-3 text-xs text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
            </div>

            {/* Submit Action */}
            <button
              type="submit"
              disabled={booking || !user}
              className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold text-sm hover:opacity-95 shadow-xl shadow-teal-500/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <span>{booking ? "Confirming Reservation..." : "Confirm & Reserve Slot"}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </div>

        {/* Right Summary Card */}
        <div className="md:col-span-1 space-y-4">
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 sticky top-20">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2.5">
              Consultation Summary
            </h3>

            <div>
              <span className="rounded-full bg-teal-500/15 px-2 py-0.5 text-[10px] font-bold text-teal-300 border border-teal-500/30">
                {doc?.specialty || "Specialist"}
              </span>
              <h4 className="text-base font-bold text-white mt-1">
                Dr. {doc?.user?.full_name || "Physician"}
              </h4>
              <p className="text-xs text-slate-400">{doc?.qualification}</p>
            </div>

            {hosp && (
              <div className="pt-2 border-t border-slate-800 text-xs space-y-1">
                <span className="text-slate-400 block font-semibold">Location:</span>
                <p className="text-white font-medium flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5 text-teal-400 shrink-0" />
                  {hosp.name}
                </p>
                <p className="text-slate-400 pl-5 text-[11px]">{hosp.city}</p>
              </div>
            )}

            <div className="pt-2 border-t border-slate-800 text-xs space-y-1">
              <span className="text-slate-400 block font-semibold">Slot Window:</span>
              <p className="text-emerald-400 font-bold flex items-center gap-1.5 text-sm">
                <Clock className="h-4 w-4 shrink-0" />
                {slot?.slot_start_ist}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300">Consultation Fee</span>
              <span className="text-xl font-black text-white">
                {formatCurrency(doc?.default_consultation_fee || 500)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
