export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Helper for authorized headers
export function getAuthHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("medislot_access_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  phone: string;
  role: "patient" | "doctor" | "hospital_admin" | "super_admin";
  hospital_id?: string | null;
  is_active: boolean;
  is_verified: boolean;
}

export interface Hospital {
  id: string;
  name: string;
  slug: string;
  address: string;
  city: string;
  state: string;
  postal_code: string;
  phone: string;
  email: string;
  latitude: number;
  longitude: number;
  is_active: boolean;
}

export interface DoctorHospitalAffiliation {
  id: string;
  doctor_id: string;
  hospital_id: string;
  hospital_name: string;
  hospital_city: string;
  department_name?: string | null;
  consultation_fee: number;
  room_number?: string | null;
  is_primary: boolean;
  is_active: boolean;
}

export interface Doctor {
  id: string;
  user_id: string;
  license_number: string;
  specialty: string;
  experience_years: number;
  qualification: string;
  bio?: string | null;
  languages_spoken: string[];
  gender: string;
  default_consultation_fee: number;
  is_verified: boolean;
  rating_avg: number;
  rating_count: number;
  user: {
    id: string;
    full_name: string;
    email: string;
    phone: string;
  };
  hospitals: DoctorHospitalAffiliation[];
}

export interface DoctorRecommendation {
  doctor_id: string;
  composite_score: number;
  score_breakdown: {
    specialty_match: number;
    earliest_slot: number;
    rating_normalized: number;
    location_proximity: number;
    experience: number;
    language: number;
  };
  explanation: string;
  earliest_available_slot_utc?: string | null;
  earliest_available_slot_ist?: string | null;
  doctor: Doctor;
}

export interface SmartSlot {
  id: string;
  doctor_id: string;
  hospital_id: string;
  slot_start: string;
  slot_end: string;
  slot_start_ist: string;
  slot_end_ist: string;
  status: "available" | "booked" | "cancelled" | "blocked";
  score: number;
  is_suggested: boolean;
  suggestion_reason?: string | null;
}

export interface SmartSlotsResponse {
  doctor_id: string;
  target_date: string;
  total_slots: number;
  available_slots: number;
  suggested_slots: SmartSlot[];
  all_slots: SmartSlot[];
}

export interface Appointment {
  id: string;
  appointment_number: string;
  patient_id: string;
  doctor_id: string;
  hospital_id: string;
  slot_id: string;
  appointment_type: "new_patient" | "follow_up";
  status: "booked" | "confirmed" | "checked_in" | "in_consultation" | "completed" | "cancelled" | "no_show";
  check_in_time?: string | null;
  consultation_start_time?: string | null;
  consultation_end_time?: string | null;
  actual_duration_minutes?: number | null;
  estimated_duration_minutes: number;
  estimated_wait_minutes?: number | null;
  notes?: string | null;
  cancellation_reason?: string | null;
  slot?: {
    id: string;
    slot_start: string;
    slot_end: string;
  };
  doctor?: {
    id: string;
    specialty: string;
    user?: {
      full_name: string;
    };
  };
  hospital?: {
    id: string;
    name: string;
    city: string;
  };
  patient?: {
    id: string;
    user?: {
      full_name: string;
      phone: string;
      email: string;
    };
  };
}

export interface QueueStatus {
  appointment_id: string;
  appointment_number: string;
  doctor_id: string;
  doctor_name: string;
  hospital_name: string;
  status: string;
  queue_number: number;
  patients_ahead: number;
  current_consultation_number?: string | null;
  historical_avg_duration_minutes: number;
  live_delay_minutes: number;
  estimated_wait_minutes_min: number;
  estimated_wait_minutes_max: number;
  estimated_wait_formatted: string;
  expected_consultation_time_ist: string;
}

export interface DoctorDailyQueuePatient {
  appointment_id: string;
  appointment_number: string;
  patient_name: string;
  patient_phone: string;
  appointment_type: string;
  status: string;
  slot_time_ist: string;
  queue_number: number;
  check_in_time?: string | null;
  consultation_start_time?: string | null;
  estimated_duration_minutes: number;
  actual_duration_minutes?: number | null;
}

export interface DoctorDailyQueue {
  doctor_id: string;
  doctor_name: string;
  hospital_id: string;
  hospital_name: string;
  target_date: string;
  total_appointments: number;
  completed_count: number;
  in_consultation_count: number;
  waiting_count: number;
  current_delay_minutes: number;
  patients: DoctorDailyQueuePatient[];
}

// ---------------------------------------------------------------------------
// AI & Clinical Triage Types
// ---------------------------------------------------------------------------

export interface TriageRequest {
  symptoms: string;
  patient_age?: number;
  patient_gender?: string;
  duration_days?: number;
}

export interface TriageResponse {
  red_flag_triggered: boolean;
  urgency_level: "emergency" | "soon" | "routine";
  primary_specialty?: string | null;
  secondary_specialty?: string | null;
  clinical_reasoning: string;
  clarifying_questions: string[];
  emergency_instructions?: string | null;
  emergency_helplines: string[];
  disclaimer: string;
  is_fallback: boolean;
}

export interface NLSearchFilterResult {
  specialty?: string | null;
  city?: string | null;
  hospital_name?: string | null;
  gender?: string | null;
  language?: string | null;
  max_fee?: number | null;
  date_intent?: string | null;
  confidence_score: number;
  summary: string;
}

export interface NLSearchResponse {
  filters: NLSearchFilterResult;
  raw_query: string;
  is_fallback: boolean;
  matched_doctors_count: number;
  top_doctor_ids: string[];
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface BookingProposal {
  doctor_id: string;
  doctor_name: string;
  specialty: string;
  hospital_name: string;
  hospital_city: string;
  slot_id: string;
  slot_start_time: string;
  consultation_fee: number;
  reason: string;
}

export interface AIChatResponse {
  message: string;
  red_flag_triggered: boolean;
  urgency_level: string;
  suggested_action?: string | null;
  specialty_recommendation?: string | null;
  booking_proposal?: BookingProposal | null;
  emergency_protocol?: {
    helplines: string[];
    instructions: string;
  } | null;
  is_fallback: boolean;
}

export interface AIQuotaStatus {
  gemini_configured: boolean;
  model_name: string;
  total_calls_today: number;
  daily_limit: number;
  status: string;
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export const api = {
  // Auth
  async login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Authentication error");
    }
    return res.json();
  },

  async register(data: { email: string; password: string; full_name: string; phone: string; gender?: string; date_of_birth?: string }) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(err.detail || "Registration error");
    }
    return res.json();
  },

  async getMe(): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Could not fetch user session");
    return res.json();
  },

  // Hospitals
  async getHospitals(): Promise<Hospital[]> {
    const res = await fetch(`${API_BASE}/hospitals`);
    if (!res.ok) throw new Error("Failed to load hospitals");
    return res.json();
  },

  // Doctors & Recommendations
  async getRecommendedDoctors(params: {
    specialty?: string;
    city?: string;
    hospital_id?: string;
    language?: string;
    gender?: string;
    max_fee?: number;
    limit?: number;
  }): Promise<DoctorRecommendation[]> {
    const q = new URLSearchParams();
    if (params.specialty) q.append("specialty", params.specialty);
    if (params.city) q.append("city", params.city);
    if (params.hospital_id) q.append("hospital_id", params.hospital_id);
    if (params.language) q.append("language", params.language);
    if (params.gender) q.append("gender", params.gender);
    if (params.max_fee) q.append("max_fee", String(params.max_fee));
    if (params.limit) q.append("limit", String(params.limit));

    const res = await fetch(`${API_BASE}/recommendations/doctors?${q.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch doctor recommendations");
    return res.json();
  },

  async getDoctorById(id: string): Promise<Doctor> {
    const res = await fetch(`${API_BASE}/doctors/${id}`);
    if (!res.ok) throw new Error("Doctor not found");
    return res.json();
  },

  // Smart Slots
  async getSmartSlots(doctorId: string, targetDate: string, hospitalId?: string): Promise<SmartSlotsResponse> {
    const q = new URLSearchParams({ doctor_id: doctorId, target_date: targetDate });
    if (hospitalId) q.append("hospital_id", hospitalId);

    const res = await fetch(`${API_BASE}/recommendations/smart-slots?${q.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load smart slots");
    return res.json();
  },

  async getSlotById(slotId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/slots/${slotId}`);
    if (!res.ok) throw new Error("Slot details not found");
    return res.json();
  },

  // Bookings
  async bookAppointment(data: { slot_id: string; appointment_type: string; notes?: string }) {
    const res = await fetch(`${API_BASE}/appointments/book`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Booking failed" }));
      throw new Error(err.detail || "Booking failed");
    }
    return res.json();
  },

  async getMyAppointments(): Promise<Appointment[]> {
    const res = await fetch(`${API_BASE}/appointments/my`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch appointments");
    return res.json();
  },

  async cancelAppointment(appointmentId: string, reason: string) {
    const res = await fetch(`${API_BASE}/appointments/${appointmentId}/cancel`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Cancellation failed" }));
      throw new Error(err.detail || "Cancellation failed");
    }
    return res.json();
  },

  // Live Queue & Wait Times
  async getAppointmentLiveQueue(appointmentId: string): Promise<QueueStatus> {
    const res = await fetch(`${API_BASE}/queue/appointment/${appointmentId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch live queue status");
    return res.json();
  },

  async getDoctorDailyQueue(doctorId: string, hospitalId: string, targetDate?: string): Promise<DoctorDailyQueue> {
    const q = new URLSearchParams({ hospital_id: hospitalId });
    if (targetDate) q.append("target_date", targetDate);

    const res = await fetch(`${API_BASE}/queue/doctor/${doctorId}?${q.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load doctor clinical queue");
    return res.json();
  },

  // Status updates by Doctor/Clinic
  async updateAppointmentStatus(appointmentId: string, status: string) {
    const res = await fetch(`${API_BASE}/appointments/${appointmentId}/status?new_status=${status}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Status update failed" }));
      throw new Error(err.detail || "Status update failed");
    }
    return res.json();
  },

  // Delay broadcasts
  async broadcastDoctorDelay(doctorId: string, hospitalId: string, delayMinutes: number, reason?: string) {
    const res = await fetch(`${API_BASE}/reminders/doctor-delay`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        doctor_id: doctorId,
        hospital_id: hospitalId,
        delay_minutes: delayMinutes,
        reason: reason || "Clinic running behind schedule due to high case complexity"
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Delay alert dispatch failed" }));
      throw new Error(err.detail || "Delay broadcast failed");
    }
    return res.json();
  },

  // -------------------------------------------------------------------------
  // AI Services
  // -------------------------------------------------------------------------
  async triageSymptoms(data: TriageRequest): Promise<TriageResponse> {
    const res = await fetch(`${API_BASE}/ai/triage`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Triage failed" }));
      throw new Error(err.detail || "Symptom triage request failed");
    }
    return res.json();
  },

  async parseNLSearch(query: string, currentCity?: string): Promise<NLSearchResponse> {
    const res = await fetch(`${API_BASE}/ai/parse-search`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ query, current_city: currentCity }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Search parsing failed" }));
      throw new Error(err.detail || "Natural language parsing failed");
    }
    return res.json();
  },

  async sendAIChat(messages: ChatMessage[], contextDoctorId?: string): Promise<AIChatResponse> {
    const res = await fetch(`${API_BASE}/ai/chat`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ messages, context_doctor_id: contextDoctorId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "AI Chat failed" }));
      throw new Error(err.detail || "Assistant response failed");
    }
    return res.json();
  },

  async getAIQuota(): Promise<AIQuotaStatus> {
    const res = await fetch(`${API_BASE}/ai/quota`);
    if (!res.ok) throw new Error("Failed to load AI quota status");
    return res.json();
  },

  // -------------------------------------------------------------------------
  // Dashboard & Analytics Services
  // -------------------------------------------------------------------------
  async getHospitalDashboardStats(hospitalId: string) {
    const res = await fetch(`${API_BASE}/hospitals/${hospitalId}/dashboard-stats`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to load dashboard stats" }));
      throw new Error(err.detail || "Failed to load hospital dashboard");
    }
    return res.json();
  },

  async getSuperAdminNetworkAnalytics() {
    const res = await fetch(`${API_BASE}/hospitals/network-analytics`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to load network analytics" }));
      throw new Error(err.detail || "Failed to load super admin network analytics");
    }
    return res.json();
  },

  async verifyDoctor(doctorId: string) {
    const res = await fetch(`${API_BASE}/doctors/${doctorId}/verify`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to verify doctor" }));
      throw new Error(err.detail || "Failed to verify doctor");
    }
    return res.json();
  }
};
