import React from "react";
import { Sparkles, Clock, CheckCircle2 } from "lucide-react";

interface SuggestedSlotBadgeProps {
  isSuggested: boolean;
  reason?: string | null;
  score?: number;
}

export function SuggestedSlotBadge({ isSuggested, reason, score }: SuggestedSlotBadgeProps) {
  if (!isSuggested) return null;

  return (
    <div className="flex flex-col gap-1 items-start">
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-500/10 animate-subtle-pulse">
        <Sparkles className="h-3 w-3 text-emerald-400 shrink-0" />
        Suggested Slot
      </span>
      {reason && (
        <span className="text-[10px] text-emerald-400/90 font-medium line-clamp-1 italic">
          {reason}
        </span>
      )}
    </div>
  );
}
