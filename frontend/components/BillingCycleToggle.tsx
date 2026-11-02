"use client";

interface Props {
  cycle: "monthly" | "yearly";
  onChange: (c: "monthly" | "yearly") => void;
}

export default function BillingCycleToggle({ cycle, onChange }: Props) {
  return (
    <div className="inline-flex items-center rounded-full border border-slate-700 bg-[#0B0F17] p-1">
      <button
        onClick={() => onChange("monthly")}
        className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
          cycle === "monthly"
            ? "bg-emerald-500 text-slate-900"
            : "text-slate-400 hover:text-slate-200"
        }`}
      >
        Monthly
      </button>
      <button
        onClick={() => onChange("yearly")}
        className={`rounded-full px-4 py-1.5 text-xs font-medium transition ${
          cycle === "yearly"
            ? "bg-emerald-500 text-slate-900"
            : "text-slate-400 hover:text-slate-200"
        }`}
      >
        Yearly
        <span className="ml-2 rounded-full bg-slate-200 px-2 py-0.5 text-[10px] text-slate-700">
          −17%
        </span>
      </button>
    </div>
  );
}