"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Sparkles,
  X,
  Send,
  AlertTriangle,
  PhoneCall,
  Calendar,
  Clock,
  MapPin,
  Bot,
  User as UserIcon,
  CheckCircle2,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import { api, ChatMessage, AIChatResponse, BookingProposal } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<
    Array<{
      id: string;
      role: "user" | "assistant";
      content: string;
      redFlag?: boolean;
      proposal?: BookingProposal | null;
      emergencyHelplines?: string[];
    }>
  >([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I am MediSlot's AI Clinical Assistant. You can describe your symptoms, ask for doctor recommendations, or check your active appointments.",
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || input;
    if (!text.trim() || isLoading) return;

    const userMsgId = Date.now().toString();
    const newMessages = [
      ...messages,
      { id: userMsgId, role: "user" as const, content: text.trim() },
    ];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const payloadMessages: ChatMessage[] = newMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res: AIChatResponse = await api.sendAIChat(payloadMessages);

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: res.message,
          redFlag: res.red_flag_triggered,
          proposal: res.booking_proposal,
          emergencyHelplines: res.emergency_protocol?.helplines,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content:
            "I experienced a connection issue. You can also browse doctors directly in the Search catalog.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Launcher Button */}
      <div className="fixed bottom-6 right-6 z-40">
        <button
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Open MediSlot AI Assistant"
          className="relative group flex items-center gap-2.5 px-4 py-3 bg-gradient-to-r from-emerald-500 via-teal-500 to-sky-500 hover:from-emerald-400 hover:to-sky-400 text-slate-950 font-semibold rounded-full shadow-xl shadow-emerald-500/25 transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <div className="relative">
            <Sparkles className="w-5 h-5 animate-spin" style={{ animationDuration: "8s" }} />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-sky-300 rounded-full animate-ping" />
          </div>
          <span className="text-sm font-bold tracking-tight">AI Clinical Assistant</span>
        </button>
      </div>

      {/* Slide-over / Modal Chat Window */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-50 w-full max-w-[430px] h-[580px] bg-slate-900/95 backdrop-blur-2xl border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-6 duration-200">
          {/* Header */}
          <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-sky-500 flex items-center justify-center text-slate-950 font-bold shadow-md shadow-emerald-500/20">
                <Bot className="w-5 h-5 text-slate-950" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-slate-100 text-sm">MediSlot AI Triage</h3>
                  <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full">
                    Online
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">Emergency & Specialty Guidance</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Clinical Disclaimer Ribbon */}
          <div className="px-3.5 py-1.5 bg-amber-500/10 border-b border-amber-500/20 text-amber-300 text-[11px] flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
            <span>AI guidance only. For medical emergencies call 108 or 112 immediately.</span>
          </div>

          {/* Messages Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 scrollbar-thin">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center shrink-0 mt-0.5 text-emerald-400 border border-slate-700/60">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                    msg.role === "user"
                      ? "bg-emerald-500 text-slate-950 font-medium rounded-tr-sm"
                      : msg.redFlag
                      ? "bg-rose-950/80 border border-rose-700/80 text-rose-100 rounded-tl-sm"
                      : "bg-slate-800/90 border border-slate-700/60 text-slate-200 rounded-tl-sm"
                  }`}
                >
                  {/* Red-Flag Critical Alert Banner */}
                  {msg.redFlag && (
                    <div className="mb-2 pb-2 border-b border-rose-800/80 flex items-start gap-2">
                      <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-rose-300 block text-[11px]">
                          CRITICAL EMERGENCY PROTOCOL
                        </span>
                        <span className="text-[10px] text-rose-200">
                          Routine outpatient booking is blocked for acute life threats.
                        </span>
                      </div>
                    </div>
                  )}

                  <p className="whitespace-pre-line">{msg.content}</p>

                  {/* Emergency Helpline Buttons */}
                  {msg.emergencyHelplines && msg.emergencyHelplines.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-rose-800/60 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <a
                          href="tel:108"
                          className="flex-1 py-1.5 px-2.5 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-lg flex items-center justify-center gap-1.5 text-[11px] transition-colors"
                        >
                          <PhoneCall className="w-3.5 h-3.5" />
                          Call 108 Ambulance
                        </a>
                        <a
                          href="tel:112"
                          className="flex-1 py-1.5 px-2.5 bg-rose-700 hover:bg-rose-600 text-white font-bold rounded-lg flex items-center justify-center gap-1.5 text-[11px] transition-colors"
                        >
                          <PhoneCall className="w-3.5 h-3.5" />
                          Call 112 Unified
                        </a>
                      </div>
                    </div>
                  )}

                  {/* Human-in-the-Loop Booking Proposal Card */}
                  {msg.proposal && (
                    <div className="mt-3 p-3 bg-slate-900/90 border border-emerald-500/40 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                          Proposed Consultation
                        </span>
                        <span className="text-xs font-bold text-slate-100">
                          {formatCurrency(msg.proposal.consultation_fee)}
                        </span>
                      </div>

                      <div>
                        <h4 className="font-bold text-slate-100 text-sm">{msg.proposal.doctor_name}</h4>
                        <p className="text-[11px] text-sky-400">{msg.proposal.specialty}</p>
                      </div>

                      <div className="space-y-1 text-[11px] text-slate-300 pt-1 border-t border-slate-800">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3 h-3 text-emerald-400" />
                          <span>{msg.proposal.slot_start_time}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3 h-3 text-slate-400" />
                          <span>
                            {msg.proposal.hospital_name}, {msg.proposal.hospital_city}
                          </span>
                        </div>
                      </div>

                      <div className="pt-2">
                        <Link
                          href={`/booking/${msg.proposal.slot_id}`}
                          onClick={() => setIsOpen(false)}
                          className="w-full py-1.5 px-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg flex items-center justify-center gap-1.5 text-xs transition-colors shadow-md shadow-emerald-500/20"
                        >
                          <span>Confirm & Book Slot</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="w-7 h-7 rounded-lg bg-emerald-600 flex items-center justify-center shrink-0 mt-0.5 text-slate-950 font-bold">
                    <UserIcon className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-2.5 items-center text-slate-400 text-xs">
                <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center border border-slate-700/60">
                  <Bot className="w-4 h-4 text-emerald-400 animate-pulse" />
                </div>
                <div className="flex items-center gap-1 bg-slate-800/80 px-3 py-2 rounded-xl border border-slate-700/50">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" />
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                  <span
                    className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce"
                    style={{ animationDelay: "0.4s" }}
                  />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts Bar */}
          <div className="px-3 py-2 bg-slate-950/60 border-t border-slate-800/80 flex gap-1.5 overflow-x-auto scrollbar-none text-[11px]">
            <button
              onClick={() => handleSend("I have knee joint pain after playing football")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full whitespace-nowrap transition-colors"
            >
              ⚽ Knee pain
            </button>
            <button
              onClick={() => handleSend("Red itchy rash and pimples on skin")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full whitespace-nowrap transition-colors"
            >
              🧴 Skin rash
            </button>
            <button
              onClick={() => handleSend("When is my active appointment?")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full whitespace-nowrap transition-colors"
            >
              📅 My booking
            </button>
            <button
              onClick={() => handleSend("Severe acidity and stomach burning")}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-full whitespace-nowrap transition-colors"
            >
              🔥 Acidity
            </button>
          </div>

          {/* Input Footer */}
          <div className="p-3 bg-slate-950 border-t border-slate-800 flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask symptoms or describe doctor needed..."
              disabled={isLoading}
              className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
            <button
              onClick={() => handleSend()}
              disabled={isLoading || !input.trim()}
              className="p-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold transition-all shadow-md shadow-emerald-500/20"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
