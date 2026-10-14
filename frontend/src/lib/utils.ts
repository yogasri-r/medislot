export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDateReadable(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export function formatTimeReadable(timeStr: string): string {
  if (!timeStr) return "";
  try {
    const d = new Date(timeStr);
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
    }
  } catch {
    // fallback
  }
  return timeStr;
}

export function getStatusBadgeProps(status: string): { label: string; bg: string; text: string; border: string } {
  switch (status.toLowerCase()) {
    case "booked":
    case "confirmed":
      return { label: "Confirmed", bg: "bg-emerald-950/60", text: "text-emerald-400", border: "border-emerald-800/80" };
    case "checked_in":
      return { label: "Checked In", bg: "bg-blue-950/60", text: "text-blue-400", border: "border-blue-800/80" };
    case "in_consultation":
      return { label: "In Consultation", bg: "bg-amber-950/60", text: "text-amber-400 animate-pulse", border: "border-amber-800/80" };
    case "completed":
      return { label: "Completed", bg: "bg-slate-900/60", text: "text-slate-400", border: "border-slate-800" };
    case "cancelled":
      return { label: "Cancelled", bg: "bg-rose-950/60", text: "text-rose-400", border: "border-rose-900/80" };
    case "no_show":
      return { label: "No-Show", bg: "bg-red-950/60", text: "text-red-400", border: "border-red-900/80" };
    default:
      return { label: status, bg: "bg-slate-800/60", text: "text-slate-300", border: "border-slate-700" };
  }
}
