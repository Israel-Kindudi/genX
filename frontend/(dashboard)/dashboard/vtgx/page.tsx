"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import VtgxCandlestickChart from "@/components/VtgxCandlestickChart";
import type { MarketDataProvider, VtgxTimeframe } from "@/lib/vtgxDatafeed";
import { createMarketDataProvider } from "@/lib/marketDataProviderFactory";
import { TOKEN_CONFIG } from "@/lib/tokenConfig";

const timeframes: VtgxTimeframe[] = ["1m", "5m", "15m", "1H", "4H", "1D"];
const isDevelopment = process.env.NODE_ENV === "development";

export default function VtgxPage() {
  const [timeframe, setTimeframe] = useState<VtgxTimeframe>("1H");
  const [chartType, setChartType] = useState<"candles" | "line">("candles");
  const [logarithmic, setLogarithmic] = useState(false);
  const [showMock, setShowMock] = useState(
    () =>
      isDevelopment &&
      process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER === "mock"
  );
  const [mockLoadError, setMockLoadError] = useState<string | null>(null);
  const [provider, setProvider] = useState<MarketDataProvider | null>(null);
  const [countdown, setCountdown] = useState<string | null>(null);
  const launchAt = process.env.NEXT_PUBLIC_VTGX_LAUNCH_AT;

  useEffect(() => {
    let active = true;
    setProvider(null);
    setMockLoadError(null);
    createMarketDataProvider(isDevelopment && showMock ? "mock" : "real")
      .then((dataProvider) => {
        if (active) setProvider(dataProvider);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setMockLoadError(
          error instanceof Error ? error.message : "Unable to load the development data preview."
        );
      });

    return () => {
      active = false;
    };
  }, [showMock]);

  useEffect(() => {
    if (!launchAt) {
      setCountdown(null);
      return;
    }
    const target = new Date(launchAt).getTime();
    if (!Number.isFinite(target)) {
      setCountdown(null);
      return;
    }

    const updateCountdown = () => {
      const remaining = target - Date.now();
      if (remaining <= 0) {
        setCountdown("Launch window reached");
        return;
      }
      const days = Math.floor(remaining / 86400000);
      const hours = Math.floor((remaining % 86400000) / 3600000);
      const minutes = Math.floor((remaining % 3600000) / 60000);
      const seconds = Math.floor((remaining % 60000) / 1000);
      setCountdown(`${days}d ${hours}h ${minutes}m ${seconds}s`);
    };

    updateCountdown();
    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, [launchAt]);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">
            <Link href="/dashboard" className="hover:text-slate-300">GENX TERMINAL</Link>
          </div>
          <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold tracking-tight text-slate-100">
            {TOKEN_CONFIG.name}
            <span className="rounded border border-emerald-500/25 bg-emerald-500/5 px-2 py-0.5 font-mono text-xs font-medium text-emerald-300">
              {TOKEN_CONFIG.symbol}
            </span>
          </h1>
          <p className="mt-1 text-sm text-slate-400">Token-specific market data and pre-launch information.</p>
        </div>
        <span className="rounded border border-amber-500/25 bg-amber-500/5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-amber-300">
          Pre-launch
        </span>
      </header>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Chart timeframe">
              {timeframes.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-label={`Show ${item} timeframe`}
                  aria-pressed={timeframe === item}
                  onClick={() => setTimeframe(item)}
                  className={`rounded border px-2.5 py-1.5 font-mono text-[10px] ${
                    timeframe === item
                      ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-300"
                      : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-100"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <div className="inline-flex rounded border border-slate-800 p-0.5" role="group" aria-label="Chart type">
                {(["candles", "line"] as const).map((type) => (
                  <button
                    key={type}
                    type="button"
                    aria-label={`Show ${type === "candles" ? "candlesticks" : "line chart"}`}
                    aria-pressed={chartType === type}
                    onClick={() => setChartType(type)}
                    className={`rounded px-2.5 py-1 text-[10px] ${
                      chartType === type
                        ? "bg-emerald-500/10 text-emerald-300"
                        : "text-slate-400 hover:text-slate-100"
                    }`}
                  >
                    {type === "candles" ? "Candles" : "Line"}
                  </button>
                ))}
              </div>
              <button
                type="button"
                aria-pressed={logarithmic}
                onClick={() => setLogarithmic((value) => !value)}
                className={`rounded border px-2.5 py-1.5 text-[10px] ${
                  logarithmic
                    ? "border-emerald-500/25 text-emerald-300"
                    : "border-slate-800 text-slate-400 hover:text-slate-100"
                }`}
              >
                {logarithmic ? "Log" : "Linear"}
              </button>
              {isDevelopment && (
                <button
                  type="button"
                  aria-pressed={showMock}
                  onClick={() => setShowMock((value) => !value)}
                  className={`rounded border px-2.5 py-1.5 text-[10px] ${
                    showMock
                      ? "border-amber-500/30 bg-amber-500/5 text-amber-300"
                      : "border-slate-800 text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {showMock ? "Mock preview on" : "Mock preview"}
                </button>
              )}
            </div>
          </div>
          {isDevelopment && showMock && (
            <p className="mb-2 text-[10px] text-amber-300" role="status">
              Simulated chart preview only. These values are not a {TOKEN_CONFIG.ticker} market price.
            </p>
          )}
          {mockLoadError && (
            <p className="mb-2 text-[10px] text-rose-300" role="alert">{mockLoadError}</p>
          )}
          <VtgxCandlestickChart
            provider={provider}
            timeframe={timeframe}
            logarithmic={logarithmic}
            simulated={isDevelopment && showMock}
            chartType={chartType}
          />
        </div>

        <aside className="space-y-3">
          <section className="rounded-lg border border-slate-800 bg-[#111723] p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-medium text-slate-300">{TOKEN_CONFIG.name} ({TOKEN_CONFIG.symbol})</h2>
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            </div>
            <p className="mt-5 font-mono text-2xl text-slate-100">
              {countdown ?? "TBA"}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              {countdown ? "Indicative launch countdown" : "Launch schedule pending confirmation"}
            </p>
            <p className="mt-4 border-t border-slate-800 pt-3 text-[10px] leading-relaxed text-slate-500">
              {TOKEN_CONFIG.name} has not been listed. No live token price or trading volume is available.
            </p>
          </section>
          <section className="rounded-lg border border-slate-800 bg-[#111723] p-4">
            <h2 className="text-xs font-medium text-slate-300">Token information</h2>
            <div className="mt-3 space-y-3">
              <InfoRow label="Total supply" value="To be announced" />
              <InfoRow label={`Your ${TOKEN_CONFIG.ticker} tier`} value="Not available pre-launch" />
              <InfoRow label="Tokenomics" value="To be announced" />
              <InfoRow label="Contract" value="Pending deployment" />
              <InfoRow label="Network" value="To be announced" />
            </div>
          </section>
        </aside>
      </section>

      <section>
        <div className="mb-3">
          <h2 className="text-sm font-medium text-slate-100">Planned utility</h2>
          <p className="mt-1 text-[11px] text-slate-500">Details and eligibility will be published with the official token documentation.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <UtilityCard title="Staking" description="Staking programme details pending official publication." />
          <UtilityCard title="Account tiers" description="Tier eligibility and benefits pending confirmation." />
          <UtilityCard title="Fee reductions" description="Any trading-fee utility and terms will be announced before listing." />
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <button type="button" disabled className="cursor-not-allowed rounded border border-slate-800 px-3 py-2 text-[10px] text-slate-600">
          Contract address pending
        </button>
        <button type="button" disabled className="cursor-not-allowed rounded border border-slate-800 px-3 py-2 text-[10px] text-slate-600">
          Explorer link pending
        </button>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-800/70 pb-2 last:border-0 last:pb-0">
      <span className="text-[10px] text-slate-500">{label}</span>
      <span className="text-right font-mono text-[10px] text-slate-300">{value}</span>
    </div>
  );
}

function UtilityCard({ title, description }: { title: string; description: string }) {
  return (
    <article className="rounded-lg border border-slate-800 bg-[#111723] p-4">
      <h3 className="text-xs font-medium text-slate-200">{title}</h3>
      <p className="mt-2 text-[11px] leading-relaxed text-slate-500">{description}</p>
    </article>
  );
}
