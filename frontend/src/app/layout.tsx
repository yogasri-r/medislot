import React, { Suspense } from "react";
import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import AIChatWidget from "@/components/AIChatWidget";

export const metadata: Metadata = {
  title: "MediSlot | AI-Powered Multi-Hospital Appointment Scheduling",
  description: "Right doctor. Right slot. Less waiting. Smart outpatient appointment scheduling, gap-filling recommendations, and real-time live queue estimation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-950 text-slate-100 antialiased">
      <body className="min-h-full flex flex-col bg-slate-950 selection:bg-teal-500/30 selection:text-teal-200">
        <AuthProvider>
          <Suspense fallback={<div className="h-14 border-b border-slate-800 bg-slate-950/80" />}>
            <Navbar />
          </Suspense>
          <main className="flex-1">{children}</main>
          <AIChatWidget />
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
