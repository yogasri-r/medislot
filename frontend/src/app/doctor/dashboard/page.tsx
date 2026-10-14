"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  api,
  DoctorDailyQueue,
  DoctorDailyQueuePatient
} from "@/lib/api";
import { formatTimeReadable, getStatusBadgeProps } from "@/lib/utils";
import {
  Stethoscope,
  Users,
  Clock,
  CheckCircle2,
  AlertCircle,
  Play,
  Check,
  UserX,
  Radio,
  RefreshCw,
  Sparkles,
  Building2,
  Calendar,
  Phone
} from "lucide-react";

export default function DoctorDashboardPage() {
  const { user, loginAsPreset } = useAuth();
  const [queueData, setQueueData] = useState<DoctorDailyQueue | null>(null);
  const [selectedDate, setSelectedDate] = useState("2026-10-15");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedDate(new Date().toISOString().split("T")[0]);
  }, []);

  // Delay broadcast modal
  const [delayModalOpen, setDelayModalOpen] = useState(false);
  const [delayMinutes, setDelayMinutes] = useState(15);
  const [delayReason, setDelayReason] = useState("Complex emergency case extension");
  const [broadcasting, setBroadcasting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchQueue = async () => {
    if (!user) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Find doctor ID for user: if logged in as doctor, user.id or hospital_id
      // For demo convenience, fallback to doctor1 if doctor profile id not in session
      const doctorId = (user as any).doctor_profile?.id || "5012ab2c-3b10-41a9-8dc0-337119bd25c8";
      const hospitalId = user.hospital_id || "7926d29e-d070-4532-a9e0-f7992faab447";

      const data = await api.getDoctorDailyQueue(doctorId, hospitalId, selectedDate);
      setQueueData(data);
    } catch (err: any) {
      setError(err.message || "Failed to load clinical daily queue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [user, selectedDate]);

  const handleStatusChange = async (appointmentId: string, newStatus: string) => {
    try {
      await api.updateAppointmentStatus(appointmentId, newStatus);
      setActionSuccess(`Appointment status updated to ${newStatus}`);
      setTimeout(() => setActionSuccess(null), 3000);
      await fetchQueue();
    } catch (err: any) {
      alert(err.message || "Failed to update status");
    }
  };

  const handleBroadcastDelay = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queueData) return;
    setBroadcasting(true);
    try {
      await api.broadcastDoctorDelay(queueData.doctor_id, queueData.hospital_id, delayMinutes, delayReason);
      setDelayModalOpen(false);
      setActionSuccess(`Delay alert broadcasted to ${queueData.waiting_count} waiting patients.`);
      setTimeout(() => setActionSuccess(null), 4000);
      await fetchQueue();
    } catch (err: any) {
      alert(err.message || "Failed to broadcast delay alert");
    } finally {
      setBroadcasting(false);
    }
  };

  if (!user && !loading) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <div className="glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-500/20 text-blue-400">
            <Stethoscope className="h-7 w-7" />
          </div>
          <h2 className="text-xl font-bold text-white">Physician Clinical Portal</h2>
          <p className="text-xs text-slate-400">
            Sign in as an attending doctor or clinic administrator to manage the outpatient consultation queue.
          </p>
          <div className="pt-2 flex flex-col gap-2.5">
            <button
              onClick={() => loginAsPreset("doctor")}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-xs hover:opacity-95 shadow-md shadow-blue-500/20"
            >
              ⚡ Instant Demo Login as Dr. Rajesh (doctor1)
            </button>
            <Link
              href="/auth/login"
              className="py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold"
            >
              Sign In with Doctor Credentials
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-400">Clinical OPD Management</span>
            <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/30">
              Active Shift
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
            Doctor Clinical Queue Dashboard
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            {queueData ? `${queueData.hospital_name} • Dr. ${queueData.doctor_name}` : "Outpatient Clinic"}
          </p>
        </div>

        {/* Date Selector & Delay Broadcast Button */}
        <div className="flex items-center gap-2.5">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-xs text-white focus:outline-none focus:border-teal-500"
          />

          <button
            onClick={() => setDelayModalOpen(true)}
            className="py-2 px-3.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/40 text-xs font-bold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Radio className="h-3.5 w-3.5 text-amber-400 animate-pulse" />
            <span>Broadcast Clinic Delay</span>
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="rounded-xl bg-emerald-950/40 border border-emerald-800/60 p-3 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Overview Statistics KPI Row */}
      {queueData && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <div className="glass-panel p-4 rounded-2xl border border-slate-800 text-center">
            <span className="text-[10px] uppercase font-bold text-slate-400">Total Bookings</span>
            <p className="text-2xl font-black text-white mt-1">{queueData.total_appointments}</p>
            <span className="text-[10px] text-slate-500">Scheduled today</span>
          </div>

          <div className="glass-panel p-4 rounded-2xl border border-blue-500/30 text-center bg-blue-950/10">
            <span className="text-[10px] uppercase font-bold text-blue-300">In Waiting Room</span>
            <p className="text-2xl font-black text-blue-400 mt-1">{queueData.waiting_count}</p>
            <span className="text-[10px] text-slate-500">Checked in & waiting</span>
          </div>

          <div className="glass-panel p-4 rounded-2xl border border-amber-500/30 text-center bg-amber-950/10">
            <span className="text-[10px] uppercase font-bold text-amber-300">In Consultation</span>
            <p className="text-2xl font-black text-amber-400 mt-1">{queueData.in_consultation_count}</p>
            <span className="text-[10px] text-slate-500">Active examination</span>
          </div>

          <div className="glass-panel p-4 rounded-2xl border border-emerald-500/30 text-center bg-emerald-950/10">
            <span className="text-[10px] uppercase font-bold text-emerald-300">Completed</span>
            <p className="text-2xl font-black text-emerald-400 mt-1">{queueData.completed_count}</p>
            <span className="text-[10px] text-slate-500">Discharged</span>
          </div>

          <div className="glass-panel p-4 rounded-2xl border border-slate-800 text-center col-span-2 sm:col-span-1">
            <span className="text-[10px] uppercase font-bold text-slate-400">Live Clinic Delay</span>
            <p className={`text-2xl font-black mt-1 ${queueData.current_delay_minutes > 0 ? "text-amber-400" : "text-emerald-400"}`}>
              {queueData.current_delay_minutes}m
            </p>
            <span className="text-[10px] text-slate-500">Dynamic offset</span>
          </div>
        </div>
      )}

      {/* Patient Queue Table */}
      <div className="glass-panel rounded-3xl border border-slate-800 overflow-hidden shadow-2xl">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-teal-400" />
            <h3 className="text-sm font-bold text-white">Outpatient Consultation Queue</h3>
          </div>
          <button
            onClick={fetchQueue}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-white"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-teal-400" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <div className="py-16 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
            <RefreshCw className="h-4 w-4 animate-spin text-teal-400" />
            <span>Loading outpatient queue...</span>
          </div>
        ) : !queueData || queueData.patients.length === 0 ? (
          <div className="py-16 text-center text-xs text-slate-400">
            No consultations scheduled for {selectedDate}.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] font-bold tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3">Queue #</th>
                  <th className="px-5 py-3">Slot Time</th>
                  <th className="px-5 py-3">Patient Details</th>
                  <th className="px-5 py-3">Visit Type</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {queueData.patients.map((p) => {
                  const badge = getStatusBadgeProps(p.status);

                  return (
                    <tr key={p.appointment_id} className="hover:bg-slate-900/50 transition-colors">
                      {/* Queue # */}
                      <td className="px-5 py-4 font-black text-white text-sm">
                        #{p.queue_number}
                      </td>

                      {/* Slot Time */}
                      <td className="px-5 py-4">
                        <span className="font-semibold text-slate-200 block">{p.slot_time_ist || "Slot Time"}</span>
                        <span className="text-[10px] text-slate-500 font-mono">{p.appointment_number}</span>
                      </td>

                      {/* Patient */}
                      <td className="px-5 py-4">
                        <span className="font-bold text-white block">{p.patient_name}</span>
                        <span className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <Phone className="h-3 w-3 text-slate-500" />
                          {p.patient_phone || "Contact on file"}
                        </span>
                      </td>

                      {/* Visit Type */}
                      <td className="px-5 py-4 capitalize font-medium text-teal-300">
                        {p.appointment_type.replace("_", " ")}
                      </td>

                      {/* Status */}
                      <td className="px-5 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badge.bg} ${badge.text} ${badge.border}`}>
                          {badge.label}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {p.status === "booked" && (
                            <button
                              onClick={() => handleStatusChange(p.appointment_id, "checked_in")}
                              className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-[11px] transition-colors"
                            >
                              Check In
                            </button>
                          )}

                          {(p.status === "booked" || p.status === "checked_in") && (
                            <button
                              onClick={() => handleStatusChange(p.appointment_id, "in_consultation")}
                              className="px-2.5 py-1 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-bold text-[11px] flex items-center gap-1 transition-colors"
                            >
                              <Play className="h-3 w-3 fill-white" />
                              <span>Start</span>
                            </button>
                          )}

                          {p.status === "in_consultation" && (
                            <button
                              onClick={() => handleStatusChange(p.appointment_id, "completed")}
                              className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] flex items-center gap-1 transition-colors"
                            >
                              <Check className="h-3.5 w-3.5" />
                              <span>Complete</span>
                            </button>
                          )}

                          {p.status !== "completed" && p.status !== "cancelled" && p.status !== "no_show" && (
                            <button
                              onClick={() => handleStatusChange(p.appointment_id, "no_show")}
                              className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 font-medium text-[11px] transition-colors"
                              title="Mark No-Show"
                            >
                              No-Show
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Broadcast Delay Modal */}
      {delayModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Radio className="h-5 w-5 text-amber-400 animate-pulse" />
              Broadcast Doctor Consultation Delay
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Alerts upcoming patients in your queue today, recalculates estimated wait times, and automatically advises staggered arrival windows to eliminate waiting hall congestion.
            </p>

            <form onSubmit={handleBroadcastDelay} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Expected Clinic Delay</label>
                <div className="grid grid-cols-4 gap-2">
                  {[10, 20, 30, 45].map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setDelayMinutes(m)}
                      className={`py-2 rounded-xl text-xs font-bold border transition-colors ${
                        delayMinutes === m
                          ? "bg-amber-500/20 border-amber-500/50 text-amber-300"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:text-white"
                      }`}
                    >
                      {m} mins
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Delay Reason</label>
                <input
                  type="text"
                  required
                  value={delayReason}
                  onChange={(e) => setDelayReason(e.target.value)}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 p-2.5 text-xs text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setDelayModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={broadcasting}
                  className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold disabled:opacity-50"
                >
                  {broadcasting ? "Dispatching Alerts..." : "Broadcast Notice"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
