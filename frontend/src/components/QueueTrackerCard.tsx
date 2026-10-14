"use client";

import React, { useState, useEffect } from "react";
import { QueueStatus, api } from "@/lib/api";
import { Clock, Users, AlertCircle, RefreshCw, Activity, CheckCircle2 } from "lucide-react";

interface QueueTrackerCardProps {
  appointmentId: string;
  initialQueue?: QueueStatus | null;
}

export function QueueTrackerCard({ appointmentId, initialQueue }: QueueTrackerCardProps) {
  const [queue, setQueue] = useState<QueueStatus | null>(initialQueue || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAppointmentLiveQueue(appointmentId);
      setQueue(data);
    } catch (err: any) {
      setError(err.message || "Could not retrieve live queue status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialQueue) {
      fetchQueue();
    }
    // Auto refresh queue every 30 seconds
    const interval = setInterval(fetchQueue, 30000);
    return () => clearInterval(interval);
  }, [appointmentId]);

  if (error) {
    return (
      <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 p-4 text-xs text-rose-300 flex items-center justify-between">
        <span>{error}</span>
        <button onClick={fetchQueue} className="p-1 rounded hover:bg-rose-900/40 text-rose-200">
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  if (!queue && loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
        <RefreshCw className="h-4 w-4 animate-spin text-teal-400" />
        <span>Calculating live queue position & wait time...</span>
      </div>
    );
  }

  if (!queue) return null;

  const isInConsultation = queue.status === "in_consultation";
  const isCompleted = queue.status === "completed";
  const hasDelay = queue.live_delay_minutes > 0;

  return (
    <div className={`rounded-xl border p-5 transition-all ${
      isInConsultation
        ? "border-amber-500/50 bg-amber-950/20 shadow-lg shadow-amber-500/10"
        : isCompleted
        ? "border-slate-800 bg-slate-900/40"
        : "border-teal-500/30 bg-slate-900/80 shadow-md shadow-teal-500/5"
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-500/20 text-teal-400">
            <Activity className="h-4 w-4 animate-pulse" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">Live Clinic Queue Tracker</h4>
            <p className="text-[11px] text-slate-400">{queue.hospital_name} • {queue.doctor_name}</p>
          </div>
        </div>

        <button
          onClick={fetchQueue}
          disabled={loading}
          className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-teal-300 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          title="Refresh Queue"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-teal-400" : ""}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* Grid of Key Queue Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Token / Queue Position */}
        <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800/60 text-center">
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">Queue Number</span>
          <p className="text-2xl font-black text-white mt-1">#{queue.queue_number}</p>
          <span className="text-[10px] text-slate-500">Scheduled sequence</span>
        </div>

        {/* Patients Ahead */}
        <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800/60 text-center">
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">Patients Ahead</span>
          <p className={`text-2xl font-black mt-1 ${queue.patients_ahead === 0 ? "text-emerald-400" : "text-teal-300"}`}>
            {queue.patients_ahead}
          </p>
          <span className="text-[10px] text-slate-500">
            {queue.patients_ahead === 0 ? "You're next!" : "In waiting room"}
          </span>
        </div>

        {/* Dynamic Estimated Wait */}
        <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-800/60 text-center col-span-2 sm:col-span-2">
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider flex items-center justify-center gap-1">
            <Clock className="h-3 w-3 text-teal-400" />
            Dynamic Wait Estimate
          </span>
          <p className={`text-xl font-bold mt-1 ${
            isInConsultation ? "text-amber-400" : "text-emerald-400"
          }`}>
            {queue.estimated_wait_formatted}
          </p>
          <span className="text-[11px] text-slate-400">
            Expected: <strong className="text-white">{queue.expected_consultation_time_ist || "Calculated live"}</strong>
          </span>
        </div>
      </div>

      {/* Delay or Consultation Notices */}
      {hasDelay && (
        <div className="mt-3.5 flex items-center gap-2 rounded-lg bg-amber-950/40 border border-amber-800/50 p-2.5 text-xs text-amber-300">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
          <span>
            Clinic running ~{queue.live_delay_minutes} mins behind schedule due to clinical case complexity. Your arrival time has been automatically staggered.
          </span>
        </div>
      )}

      {isInConsultation && (
        <div className="mt-3.5 flex items-center gap-2 rounded-lg bg-teal-950/40 border border-teal-800/50 p-2.5 text-xs text-teal-300 animate-pulse">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-teal-400" />
          <span>Doctor is currently conducting your consultation in the examination room.</span>
        </div>
      )}
    </div>
  );
}
