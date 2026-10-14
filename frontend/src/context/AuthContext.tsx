"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { api, UserProfile } from "@/lib/api";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; phone: string; gender?: string; date_of_birth?: string }) => Promise<void>;
  logout: () => void;
  loginAsPreset: (preset: "patient" | "doctor" | "admin" | "super_admin") => Promise<void>;
  loginAsDemo: (preset: "patient" | "doctor" | "admin" | "super_admin" | "hospital_admin") => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("medislot_access_token");
    if (savedToken) {
      setToken(savedToken);
      api.getMe()
        .then((profile) => setUser(profile))
        .catch(() => {
          localStorage.removeItem("medislot_access_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await api.login(email, password);
      localStorage.setItem("medislot_access_token", data.access_token);
      setToken(data.access_token);
      const profile = await api.getMe();
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { email: string; password: string; full_name: string; phone: string; gender?: string; date_of_birth?: string }) => {
    setIsLoading(true);
    try {
      await api.register(data);
      // Auto login upon registration
      await login(data.email, data.password);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("medislot_access_token");
    setToken(null);
    setUser(null);
  };

  const loginAsPreset = async (preset: "patient" | "doctor" | "admin" | "super_admin" | "hospital_admin") => {
    if (preset === "patient") {
      await login("patient1@medislot.com", "Patient@123456");
    } else if (preset === "doctor") {
      await login("doctor1@medislot.com", "Doctor@123456");
    } else if (preset === "admin" || preset === "hospital_admin") {
      await login("admin.coimbatore@medislot.com", "Hospital@123456");
    } else if (preset === "super_admin") {
      await login("admin@medislot.com", "Admin@123456");
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout, loginAsPreset, loginAsDemo: loginAsPreset }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
