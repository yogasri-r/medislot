"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Building2,
  Users,
  Stethoscope,
  CalendarCheck,
  Clock,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  ChevronRight,
  ShieldAlert,
  Search,
  Filter,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default function HospitalAdminDashboard() {
  const { user, loginAsDemo } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDept, setSelectedDept] = useState("all");

  const hospitalId = user?.hospital_id || "43b7fc42-70b7-4dbf-8ea8-54bca6bfe212"; // Coimbatore default

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const stats = await api.getHospitalDashboardStats(hospitalId);
      setData(stats);
    } catch (err: any) {
      setError(err.message || "Failed to load hospital operational data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [hospitalId]);

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3">
        <div className="w-10 h-10 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-400">Loading hospital operational metrics...</span>
      </div>
    );
  }

  // Not authenticated as hospital admin
  if (!user || (user.role !== "hospital_admin" && user.role !== "super_admin")) {
    return (
      <div className="mx-auto max-w-lg py-20 px-4 text-center">
        <div className="p-8 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <Building2 className="w-12 h-12 text-teal-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Hospital Admin Access Required</h2>
          <p className="text-sm text-slate-400">
            This operational dashboard is strictly scoped to hospital administrators. You can switch to the demo hospital admin persona below.
          </p>
          <button
            onClick={() => loginAsDemo("hospital_admin")}
            className="w-full py-2.5 px-4 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold rounded-xl transition-all shadow-lg shadow-teal-500/20 text-sm"
          >
            Switch to Coimbatore Hospital Admin
          </button>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-xl py-20 px-4 text-center">
        <div className="p-8 rounded-2xl bg-slate-900 border border-rose-800/60 space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Operational Data Unavailable</h2>
          <p className="text-sm text-slate-400">{error || "Could not fetch dashboard metrics."}</p>
          <button
            onClick={loadDashboardData}
            className="py-2 px-5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-sm font-semibold transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { hospital, stats, departments, doctors } = data;

  const filteredDoctors = doctors.filter((doc: any) => {
    const matchesSearch =
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.specialty.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.license_number.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDept = selectedDept === "all" || doc.specialty.toLowerCase() === selectedDept.toLowerCase();
    return matchesSearch && matchesDept;
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Hospital Header Banner */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-slate-900 via-slate-900 to-teal-950/40 border border-teal-500/30 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-2xl">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/20 border border-teal-500/40 text-teal-300 text-xs font-semibold">
            <Building2 className="w-3.5 h-3.5" />
            <span>Hospital-Scoped Tenancy • {hospital.city} Cluster</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">{hospital.name}</h1>
          <p className="text-xs sm:text-sm text-slate-400">
            {hospital.address} • Phone: {hospital.phone} • Email: {hospital.email}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/doctor/dashboard`}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors flex items-center gap-2"
          >
            <Clock className="w-4 h-4 text-sky-400" />
            <span>Doctor Clinical Queue</span>
          </Link>
          <Link
            href="/search"
            className="px-4 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold transition-all shadow-md shadow-teal-500/20 flex items-center gap-2"
          >
            <span>Public OPD View</span>
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* KPI Summary Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <Stethoscope className="w-4 h-4 text-teal-400" />
            Active Doctors
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{stats.total_doctors}</div>
          <span className="text-[11px] text-teal-400">{stats.total_departments} Clinical Departments</span>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <CalendarCheck className="w-4 h-4 text-sky-400" />
            Total Outpatients
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{stats.total_appointments}</div>
          <span className="text-[11px] text-sky-400">{stats.completed_appointments} Completed Visits</span>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <TrendingDown className="w-4 h-4 text-amber-400" />
            Outpatient No-Show Rate
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{stats.no_show_rate}%</div>
          <span className="text-[11px] text-slate-400">{stats.no_show_appointments} No-Shows Recorded</span>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
            <Clock className="w-4 h-4 text-emerald-400" />
            Active Clinic Queue
          </span>
          <div className="text-2xl sm:text-3xl font-black text-white">{stats.active_appointments}</div>
          <span className="text-[11px] text-emerald-400">Scheduled / Checked-In Today</span>
        </div>
      </div>

      {/* Departments Overview */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Building2 className="w-5 h-5 text-teal-400" />
          <span>Hospital Departments ({departments.length})</span>
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
          {departments.map((dept: any) => (
            <div
              key={dept.id}
              onClick={() => setSelectedDept(selectedDept === dept.name ? "all" : dept.name)}
              className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                selectedDept.toLowerCase() === dept.name.toLowerCase()
                  ? "bg-teal-500/20 border-teal-500/60 shadow-lg shadow-teal-500/10"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="font-bold text-sm text-slate-100">{dept.name}</div>
              <div className="text-xs text-teal-400 mt-1">{dept.doctors_count} Doctors Assigned</div>
            </div>
          ))}
        </div>
      </div>

      {/* Doctor Roster Management */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-sky-400" />
              <span>Affiliated Physicians & Performance Roster</span>
            </h2>
            <p className="text-xs text-slate-400">
              Monitoring clinical workload, verification credentials, and patient satisfaction ratings.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter by doctor name or specialty..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-teal-500 w-60 sm:w-72"
              />
            </div>
            {selectedDept !== "all" && (
              <button
                onClick={() => setSelectedDept("all")}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
              >
                Clear Filter
              </button>
            )}
          </div>
        </div>

        {/* Doctor Table */}
        <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/70 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Doctor & License</th>
                <th className="py-3 px-4">Specialty & Exp</th>
                <th className="py-3 px-4">Consultation Fee</th>
                <th className="py-3 px-4">Rating</th>
                <th className="py-3 px-4">Completed Visits</th>
                <th className="py-3 px-4">No-Show Count</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredDoctors.map((doc: any) => (
                <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-slate-100 text-sm flex items-center gap-2">
                      <span>{doc.name}</span>
                      {doc.is_verified && (
                        <span title="Verified Medical License">
                          <CheckCircle2 className="w-3.5 h-3.5 text-teal-400" />
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      Lic: {doc.license_number}
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <span className="px-2.5 py-1 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-300 font-medium">
                      {doc.specialty}
                    </span>
                    <div className="text-[11px] text-slate-400 mt-1">
                      {doc.experience_years} years experience
                    </div>
                  </td>

                  <td className="py-3.5 px-4 font-bold text-slate-200">
                    {formatCurrency(doc.consultation_fee)}
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-1 font-bold text-amber-400">
                      <span>★</span>
                      <span>{doc.rating_avg.toFixed(1)}</span>
                    </div>
                    <span className="text-[11px] text-slate-400">({doc.rating_count} reviews)</span>
                  </td>

                  <td className="py-3.5 px-4 font-semibold text-slate-200">
                    {doc.completed_appointments}
                  </td>

                  <td className="py-3.5 px-4">
                    <span
                      className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                        doc.no_show_count > 10
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {doc.no_show_count}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <Link
                      href={`/doctors/${doc.id}`}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-teal-300 font-medium text-xs transition-colors"
                    >
                      View Profile
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
