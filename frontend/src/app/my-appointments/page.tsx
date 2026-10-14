"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { api, Appointment } from "@/lib/api";
import { formatTimeReadable, formatDateReadable, getStatusBadgeProps } from "@/lib/utils";
import { QueueTrackerCard } from "@/components/QueueTrackerCard";
import {
  Calendar,
  Clock,
  Building2,
  Stethoscope,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Activity,
  ArrowRight,
  User,
  Sparkles
} from "lucide-react";

export default function MyAppointmentsPage() {
  const { user, loginAsPreset } = useAuth();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"upcoming" | "past">("upcoming");

  // Cancellation modal state
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("Work schedule conflict");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchAppointments = async () => {
    if (!user) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMyAppointments();
      setAppointments(data);
    } catch (err: any) {
      setError(err.message || "Could not fetch your appointment records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, [user]);

  const handleCancel = async (id: string) => {
    setActionLoading(true);
    try {
      await api.cancelAppointment(id, cancelReason);
      setCancellingId(null);
      await fetchAppointments();
    } catch (err: any) {
      alert(err.message || "Failed to cancel appointment");
    } finally {
      setActionLoading(false);
    }
  };

  if (!user && !loading) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <div className="glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-500/20 text-teal-400">
            <User className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold text-white">Sign In to View Appointments</h2>
          <p className="text-xs text-slate-400">
            Track your consultations, view live clinic queue position, and manage your bookings.
          </p>
          <div className="pt-2 flex flex-col gap-2.5">
            <button
              onClick={() => loginAsPreset("patient")}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 text-slate-950 font-bold text-xs hover:opacity-95 shadow-md shadow-teal-500/20"
            >
              ⚡ Instant Demo Login as Patient (patient1)
            </button>
            <Link
              href="/auth/login"
              className="py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold"
            >
              Sign In with Existing Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const upcomingAppts = appointments.filter(
    (a) => a.status !== "completed" && a.status !== "cancelled" && a.status !== "no_show"
  );
  const pastAppts = appointments.filter(
    (a) => a.status === "completed" || a.status === "cancelled" || a.status === "no_show"
  );

  const displayList = activeTab === "upcoming" ? upcomingAppts : pastAppts;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-teal-400">Patient Portal</span>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            My Consultations & Live Queue
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time outpatient queue position, estimated wait times, and appointment controls.
          </p>
        </div>

        <Link
          href="/search"
          className="py-2 px-3.5 rounded-xl bg-teal-500/15 hover:bg-teal-500/25 text-teal-300 border border-teal-500/30 text-xs font-bold flex items-center gap-1.5 transition-colors"
        >
          <span>Book New Slot</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-800 pb-1">
        <button
          onClick={() => setActiveTab("upcoming")}
          className={`py-2 px-4 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
            activeTab === "upcoming"
              ? "bg-teal-500/20 text-teal-300 border border-teal-500/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Calendar className="h-3.5 w-3.5" />
          <span>Upcoming Appointments ({upcomingAppts.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("past")}
          className={`py-2 px-4 rounded-lg text-xs font-bold transition-colors flex items-center gap-2 ${
            activeTab === "past"
              ? "bg-teal-500/20 text-teal-300 border border-teal-500/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Clock className="h-3.5 w-3.5" />
          <span>Past Consultations ({pastAppts.length})</span>
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="py-16 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
          <RefreshCw className="h-4 w-4 animate-spin text-teal-400" />
          <span>Retrieving your outpatient records...</span>
        </div>
      ) : displayList.length === 0 ? (
        <div className="glass-panel p-12 rounded-3xl border border-slate-800 text-center text-xs text-slate-400 space-y-3">
          <Calendar className="h-8 w-8 mx-auto text-slate-600" />
          <h3 className="text-base font-bold text-white">No {activeTab} appointments found</h3>
          <p>
            {activeTab === "upcoming"
              ? "You do not have any pending consultations scheduled."
              : "Your consultation history will appear here once visits are completed."}
          </p>
          {activeTab === "upcoming" && (
            <Link
              href="/search"
              className="inline-block mt-2 py-2 px-4 rounded-xl bg-teal-500 text-slate-950 font-bold text-xs hover:opacity-95"
            >
              Explore Available Slots
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {displayList.map((appt) => {
            const badge = getStatusBadgeProps(appt.status);
            const isUpcoming = appt.status !== "completed" && appt.status !== "cancelled" && appt.status !== "no_show";

            return (
              <div
                key={appt.id}
                className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5"
              >
                {/* Header Information */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 border border-slate-800 text-teal-400">
                      <Stethoscope className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-white">
                          Dr. {appt.doctor?.user?.full_name || "Specialist"}
                        </h3>
                        <span className="text-xs text-indigo-300 font-semibold bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/60">
                          {appt.doctor?.specialty}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-2">
                        <span>{appt.hospital?.name} ({appt.hospital?.city})</span>
                        <span>•</span>
                        <span className="font-mono text-slate-500 text-[11px]">{appt.appointment_number}</span>
                      </p>
                    </div>
                  </div>

                  {/* Status Badge */}
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${badge.bg} ${badge.text} ${badge.border}`}>
                      {badge.label}
                    </span>
                  </div>
                </div>

                {/* Detail Row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/60">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Scheduled Slot</span>
                    <p className="text-sm font-bold text-white mt-0.5">
                      {appt.slot ? formatTimeReadable(appt.slot.slot_start) : "Assigned Slot"}
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/60">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Visit Type</span>
                    <p className="text-sm font-bold text-teal-400 mt-0.5 capitalize">
                      {appt.appointment_type.replace("_", " ")}
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/60">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Est. Consultation</span>
                    <p className="text-sm font-bold text-slate-300 mt-0.5">
                      ~{appt.estimated_duration_minutes} minutes
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800/60">
                    <span className="text-[10px] uppercase font-bold text-slate-500">Arrival Advice</span>
                    <p className="text-xs font-semibold text-emerald-400 mt-0.5">
                      Arrive 10m prior
                    </p>
                  </div>
                </div>

                {/* Embedded Live Day-Of Queue Tracker for upcoming consultations */}
                {isUpcoming && (
                  <div className="pt-2">
                    <QueueTrackerCard appointmentId={appt.id} />
                  </div>
                )}

                {/* Actions Bar */}
                {isUpcoming && (
                  <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
                    <span className="text-[11px] text-slate-500">
                      Need to reschedule or cancel? Early cancellations liberate slots for waitlisted patients.
                    </span>

                    <button
                      onClick={() => setCancellingId(appt.id)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 border border-rose-900/40 transition-colors"
                    >
                      Cancel Consultation
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Cancellation Modal */}
      {cancellingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <XCircle className="h-5 w-5 text-rose-400" />
              Cancel Appointment Reservation
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Are you sure you want to cancel? This will free the consultation slot and automatically offer it to the next patient on the clinical waitlist.
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Reason for Cancellation</label>
              <select
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 p-2 text-xs text-white [&>option]:bg-slate-900"
              >
                <option value="Work schedule conflict">Work schedule conflict</option>
                <option value="Feeling significantly better; symptoms resolved">Feeling significantly better</option>
                <option value="Sudden personal emergency">Sudden personal emergency</option>
                <option value="Rescheduled to another clinic">Rescheduled to another clinic</option>
              </select>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setCancellingId(null)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
              >
                Keep Booking
              </button>
              <button
                onClick={() => handleCancel(cancellingId)}
                disabled={actionLoading}
                className="flex-1 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold disabled:opacity-50"
              >
                {actionLoading ? "Cancelling..." : "Confirm Cancellation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
