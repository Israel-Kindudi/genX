"use client";

import { useMemo } from "react";
import MonthlyHeatmap from "@/components/MonthlyHeatmap";
import { calculateDashboardMetrics, calculateMonthlyReturns } from "@/lib/dashboardAnalytics";
import { useLiveTrades } from "@/lib/useLiveTrades";

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export default function PerformancePage() {
  const { trades, equityPoints } = useLiveTrades(1000, 1000);
  const metrics = useMemo(
    () => calculateDashboardMetrics(trades, equityPoints),
    [trades, equityPoints]
  );
  const monthlyReturns = useMemo(
    () => calculateMonthlyReturns(equityPoints),
    [equityPoints]
  );
  const equity = equityPoints[equityPoints.length - 1]?.equity;
  const balance = equityPoints[equityPoints.length - 1]?.balance;
  const cards = [
    { label: "Realized PnL", value: `${metrics.realizedPnL >= 0 ? "+" : "−"}${currency.format(Math.abs(metrics.realizedPnL))}` },
    { label: "Win rate", value: `${metrics.winRate.toFixed(1)}%` },
    { label: "Max drawdown", value: `${metrics.maxDrawdown.toFixed(2)}%`, negative: metrics.maxDrawdown > 0 },
    {
      label: "Profit factor",
      value: metrics.profitFactor === null ? "N/A" : metrics.profitFactor.toFixed(2),
      info: "Gross profit divided by gross loss across closed trades.",
    },
    {
      label: "Sharpe",
      value: metrics.tradeSharpe === null ? "N/A" : metrics.tradeSharpe.toFixed(2),
      info: "Annualized mean daily return divided by daily return volatility; shown after 30 daily returns or 30 closed trades.",
    },
    {
      label: "Calmar",
      value: metrics.calmar === null ? "N/A" : metrics.calmar.toFixed(2),
      info: "Annualized equity return divided by the maximum peak-to-trough drawdown.",
    },
    {
      label: "Realized R:R",
      value: metrics.averageRiskReward === null ? "N/A" : `${metrics.averageRiskReward.toFixed(2)}:1`,
      info: "Average realized winning trade divided by the average absolute losing trade.",
    },
    {
      label: "Expectancy / trade",
      value: metrics.closedTrades > 0 ? `${metrics.expectancy >= 0 ? "+" : "−"}${currency.format(Math.abs(metrics.expectancy))}` : "N/A",
      info: "Average realized profit or loss per closed trade.",
    },
  ];

  return (
    <div className="space-y-5">
      <header>
        <p className="mb-2 text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-300">Performance</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-100">Performance analytics</h1>
        <p className="mt-1 text-sm text-slate-400">
          Account risk and trade statistics from the available live stream.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        {cards.map((card) => (
          <div key={card.label} className="rounded-md border border-slate-800 bg-[#111723] px-3 py-3">
            <div className="flex items-center gap-1">
              <p className="text-[10px] text-slate-500">{card.label}</p>
              {"info" in card && card.info && (
                <button
                  type="button"
                  title={card.info}
                  aria-label={`${card.label}: ${card.info}`}
                  className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-slate-600 text-[9px] leading-none text-slate-400"
                >
                  i
                </button>
              )}
            </div>
            <p className={`mt-1 font-mono text-sm tabular-nums ${
              card.negative ? "text-rose-400" : "text-slate-100"
            }`}>{card.value}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-3 sm:grid-cols-2">
        <Snapshot label="Latest equity" value={equity == null ? "—" : currency.format(equity)} />
        <Snapshot label="Latest balance" value={balance == null ? "—" : currency.format(balance)} />
      </section>

      <MonthlyHeatmap returns={monthlyReturns} />

      <div className="rounded-md border border-slate-800 bg-[#111723] px-4 py-3 text-[11px] leading-relaxed text-slate-400">
        Trade Sharpe is a non-annualized per-trade estimate. Official annualized Sharpe requires dated return observations and a configured risk-free rate. Metrics reflect the currently available WebSocket history.
      </div>
    </div>
  );
}

function Snapshot({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-[#111723] p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-2 font-mono text-xl tabular-nums text-slate-100">{value}</p>
    </div>
  );
}
