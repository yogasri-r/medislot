"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  Building2,
  Users,
  Stethoscope,
  Activity,
  Cpu,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  ChevronRight,
  RefreshCw,
  Search,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api, AIQuotaStatus } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default function SuperAdminDashboard() {
  const { user, loginAsDemo } = useAuth();
  const [data, setData] = useState<any>(null);
  const [quota, setQuota] = useState<AIQuotaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifyingDocId, setVerifyingDocId] = useState<string | null>(null);
  const [doctorSearch, setDoctorSearch] = useState("");

  const loadNetworkData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [analyticsRes, quotaRes] = await Promise.all([
        api.getSuperAdminNetworkAnalytics(),
        api.getAIQuota().catch(() => null),
      ]);
      setData(analyticsRes);
      setQuota(quotaRes);
    } catch (err: any) {
      setError(err.message || "Failed to load platform network analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNetworkData();
  }, []);

  const handleVerifyDoctor = async (doctorId: string) => {
    setVerifyingDocId(doctorId);
    try {
      await api.verifyDoctor(doctorId);
      // Reload data
      const analyticsRes = await api.getSuperAdminNetworkAnalytics();
      setData(analyticsRes);
    } catch (err: any) {
      alert("Failed to verify doctor: " + err.message);
    } finally {
      setVerifyingDocId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-400">Loading cross-hospital platform telemetry...</span>
      </div>
    );
  }

  // Not super admin
  if (!user || user.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-lg py-20 px-4 text-center">
        <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <ShieldCheck className="w-12 h-12 text-indigo-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Super Admin Access Required</h2>
          <p className="text-sm text-slate-400">
            This platform governance portal is restricted to MediSlot network administrators. Switch to the demo super admin persona below.
          </p>
          <button
            onClick={() => loginAsDemo("super_admin")}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-indigo-600/25 text-sm"
          >
            Switch to Super Admin
          </button>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-xl py-20 px-4 text-center">
        <div className="p-8 rounded-2xl bg-slate-900 border border-rose-800/60 space-y-4">
          <AlertCircle className="w-12 h-12 text-rose-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Platform Telemetry Unavailable</h2>
          <p className="text-sm text-slate-400">{error || "Could not fetch network analytics."}</p>
          <button
            onClick={loadNetworkData}
            className="py-2 px-5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-sm font-semibold transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { network_stats, hospitals, specialties_distribution } = data;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Header Banner */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/60 to-slate-900 border border-indigo-500/30 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-2xl">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Platform Governance & Cross-Hospital Network</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            MediSlot Network Administration
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Coimbatore • Erode • Tiruppur • Dharapuram Multi-Hospital Health System
          </p>
        </div>

        <button
          onClick={loadNetworkData}
          className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors flex items-center gap-2 self-start md:self-auto"
        >
          <RefreshCw className="w-4 h-4 text-indigo-400" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* Network KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <Building2 className="w-4 h-4 text-indigo-400" />
            Partner Hospitals
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{network_stats.total_hospitals}</div>
          <span className="text-[11px] text-indigo-400">Western Tamil Nadu Hubs</span>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <Stethoscope className="w-4 h-4 text-teal-400" />
            Medical Specialists
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{network_stats.total_doctors}</div>
          <span className="text-[11px] text-teal-400">
            {network_stats.verified_doctors} Verified Credentials
          </span>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <Users className="w-4 h-4 text-sky-400" />
            Registered Patients
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{network_stats.total_patients}</div>
          <span className="text-[11px] text-sky-400">{network_stats.total_appointments} Bookings Processed</span>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <Activity className="w-4 h-4 text-emerald-400" />
            Network No-Show Rate
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{network_stats.network_no_show_rate}%</div>
          <span className="text-[11px] text-emerald-400">Predictive ML Interventions Active</span>
        </div>
      </div>

      {/* AI & ML System Telemetry Panel */}
      <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">AI & ML Production Model Telemetry</h2>
          </div>
          <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Services Operational
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Gemini AI Quota */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                Gemini LLM Engine
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-300 font-mono">
                {quota?.model_name || "gemini-2.5-flash"}
              </span>
            </div>
            <div className="text-xl font-bold text-white">
              {quota ? `${quota.total_calls_today} / ${quota.daily_limit}` : "Active"}
            </div>
            <p className="text-[11px] text-slate-400">
              Daily quota budget tracking with automated deterministic fallbacks.
            </p>
          </div>

          {/* No-Show ML Model */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                No-Show Classifier
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono">
                ROC-AUC: 0.7034
              </span>
            </div>
            <div className="text-xl font-bold text-white">Gradient Boosting</div>
            <p className="text-[11px] text-slate-400">
              Threshold 0.35 yields 64.8% recall of impending patient no-shows.
            </p>
          </div>

          {/* Wait Time ML Model */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-amber-400" />
                Wait-Time Regressor
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-mono">
                MAE: 2.24 mins
              </span>
            </div>
            <div className="text-xl font-bold text-white">39.3% Error Reduction</div>
            <p className="text-[11px] text-slate-400">
              Outperforms naive outpatient scheduling rules across all hospital queues.
            </p>
          </div>
        </div>
      </div>

      {/* Hospital Network Breakdown Table */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-indigo-400" />
            <span>Hospital Network Performance</span>
          </h2>
          <p className="text-xs text-slate-400">
            Real-time outpatient volumes and estimated consultation revenue by facility.
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/70 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Hospital Facility</th>
                <th className="py-3 px-4">City / Region</th>
                <th className="py-3 px-4">Physicians</th>
                <th className="py-3 px-4">Total Visits</th>
                <th className="py-3 px-4">Completed Consultations</th>
                <th className="py-3 px-4">Estimated OPD Revenue</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {hospitals.map((h: any) => (
                <tr key={h.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-slate-100 text-sm">
                    {h.name}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-medium">
                      {h.city}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-slate-200">
                    {h.doctors_count} Doctors
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">
                    {h.total_appointments}
                  </td>
                  <td className="py-3.5 px-4 font-bold text-emerald-400">
                    {h.completed_appointments}
                  </td>
                  <td className="py-3.5 px-4 font-bold text-slate-100">
                    {formatCurrency(h.estimated_revenue)}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      href={`/admin/dashboard`}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 font-medium text-xs transition-colors border border-indigo-500/30"
                    >
                      Hospital View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
