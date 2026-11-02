"use client";

import Link from "next/link";
import { createPortal } from "react-dom";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  Brush,
  CartesianGrid,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  calculateFlowAdjustedEquity,
  calculateDashboardMetrics,
  calculateMonthlyReturns,
  getEquityDomain,
  getPercentDomain,
  type FlowAdjustedEquity,
} from "@/lib/dashboardAnalytics";
import MonthlyHeatmap from "@/components/MonthlyHeatmap";
import VtgxSparkline from "@/components/VtgxSparkline";
import { TOKEN_CONFIG } from "@/lib/tokenConfig";
import SmoothFollowTooltip, {
  type TooltipPositionRef,
} from "@/components/SmoothFollowTooltip";
import type { LiveTrade } from "@/lib/useLiveTrades";
import { useAccountDataProvider } from "@/lib/useAccountDataProvider";
import {
  createDevelopmentBenchmarkMock,
  unavailableBenchmarkDatafeed,
  type BenchmarkDatafeed,
  type BenchmarkPoint,
  type BenchmarkSymbol,
} from "@/lib/dashboardBenchmarkDatafeed";

type PeriodKey = "1H" | "1D" | "1W" | "1M" | "3M" | "YTD" | "ALL";
type ValueMode = "usd" | "percent";
type DisplayMode = ValueMode;
type Benchmark = "vtgx" | "btc" | "gold" | "sp500" | "none";
type ChartRow = {
  timestamp: number;
  equity: number;
  balance: number;
  timeWeightedEquity: number;
  timeWeightedBalance: number;
  timeWeightedReturn: number;
  underwater: number;
  cycle: number;
  openPositions: number;
  tradeSymbol?: string;
  tradeAction?: string;
  tradeEvent?: string;
  tradePnl?: number | null;
  placeholder?: boolean;
  benchmarkValue?: number | null;
};

const PERIODS: { key: PeriodKey; label: string }[] = [
  { key: "1H", label: "1H" },
  { key: "1D", label: "1D" },
  { key: "1W", label: "1W" },
  { key: "1M", label: "1M" },
  { key: "3M", label: "3M" },
  { key: "YTD", label: "YTD" },
  { key: "ALL", label: "ALL" },
];

const BENCHMARKS: { key: Benchmark; label: string; symbol?: BenchmarkSymbol }[] = [
  { key: "vtgx", label: `${TOKEN_CONFIG.name} (${TOKEN_CONFIG.symbol})`, symbol: TOKEN_CONFIG.ticker },
  { key: "btc", label: "BTC", symbol: "BTCUSD" },
  { key: "gold", label: "Gold", symbol: "XAUUSD" },
  { key: "sp500", label: "S&P 500", symbol: "SP500" },
  { key: "none", label: "None" },
];

export default function LiveTerminal() {
  const { provider, snapshot, DemoAccountControls, DemoAccountBanner } =
    useAccountDataProvider();
  const {
    trades,
    equityPoints,
    initialCapital,
    currency: accountCurrency,
    capitalFlows,
    connected,
    isDemonstration,
    fixtureId,
  } = snapshot;
  const currency = useMemo(
    () =>
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: accountCurrency ?? "USD",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [accountCurrency]
  );
  const formatSignedCurrency = (value: number) =>
    signedCurrency(value, accountCurrency ?? "USD");
  const [period, setPeriod] = useState<PeriodKey>("ALL");
  const [valueMode, setValueMode] = useState<ValueMode>("usd");
  const [benchmark, setBenchmark] = useState<Benchmark>("vtgx");
  const [benchmarkPoints, setBenchmarkPoints] = useState<BenchmarkPoint[]>([]);
  const [useBenchmarkMock, setUseBenchmarkMock] = useState(false);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const drawdownChartRef = useRef<HTMLDivElement>(null);
  const equityTooltipPositionRef = useRef<TooltipPositionRef["current"]>(null);
  const drawdownTooltipPositionRef = useRef<TooltipPositionRef["current"]>(null);
  const lastPointerRef = useRef<{ x: number; y: number } | null>(null);
  const pendingPointerRef = useRef<{ x: number; y: number } | null>(null);
  const pointerFrameRef = useRef(0);
  const updateChartHoverRef = useRef<(clientX: number, clientY: number) => void>(() => {});
  const [chartHover, setChartHover] = useState<{
    row: ChartRow;
    x: number;
    markerY: number;
    markerTop: number;
    markerBottom: number;
    maxHeight: number;
  } | null>(null);
  const benchmarkDatafeed = useMemo<BenchmarkDatafeed>(
    () =>
      useBenchmarkMock && process.env.NODE_ENV === "development"
        ? createDevelopmentBenchmarkMock(process.env.NODE_ENV)
        : unavailableBenchmarkDatafeed,
    [useBenchmarkMock]
  );
  const metrics = useMemo(
    () => calculateDashboardMetrics(trades, equityPoints, initialCapital, capitalFlows),
    [trades, equityPoints, initialCapital, capitalFlows]
  );
  const hasInitialCapital =
    initialCapital !== null && Number.isFinite(initialCapital) && initialCapital > 0;
  const baseline = hasInitialCapital ? initialCapital : 0;
  const orderedPoints = useMemo(
    () =>
      [...equityPoints].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      ),
    [equityPoints]
  );
  const adjustedPoints = useMemo<FlowAdjustedEquity[]>(
    () =>
      hasInitialCapital
        ? calculateFlowAdjustedEquity(orderedPoints, baseline, capitalFlows)
        : [],
    [hasInitialCapital, orderedPoints, baseline, capitalFlows]
  );
  const oldestPointTime = orderedPoints[0]
    ? new Date(orderedPoints[0].timestamp).getTime()
    : Date.now();
  const cutoff = getPeriodCutoff(period, Date.now(), oldestPointTime);
  const rangePoints = useMemo(() => {
    return orderedPoints.filter(
      (point) => new Date(point.timestamp).getTime() >= cutoff
    );
  }, [orderedPoints, cutoff]);

  const sampledPoints = useMemo(
    () => sampleEquityPoints(
      adjustedPoints.filter((point) => new Date(point.timestamp).getTime() >= cutoff),
      period,
      adjustedPoints
    ),
    [adjustedPoints, cutoff, period]
  );

  const latest = orderedPoints[orderedPoints.length - 1];
  const latestAdjusted = adjustedPoints[adjustedPoints.length - 1];
  const currentEquity = latest?.equity ?? baseline;
  const periodAdjusted = sampledPoints[0];
  const periodChange = latestAdjusted && periodAdjusted
    ? latestAdjusted.timeWeightedEquity - periodAdjusted.timeWeightedEquity
    : 0;
  const periodChangePercent = latestAdjusted && periodAdjusted && periodAdjusted.timeWeightedEquity > 0
    ? (latestAdjusted.timeWeightedEquity / periodAdjusted.timeWeightedEquity - 1) * 100
    : 0;
  const accountReturnPercent = latestAdjusted?.timeWeightedReturn ?? 0;
  const monthlyReturns = useMemo(
    () => calculateMonthlyReturns(
      adjustedPoints.map((point) => ({
        ...point,
        equity: point.timeWeightedEquity,
      }))
    ),
    [adjustedPoints]
  );

  useEffect(() => {
    const selectedBenchmark = BENCHMARKS.find((item) => item.key === benchmark);
    setBenchmarkPoints([]);
    if (!selectedBenchmark?.symbol) {
      return;
    }

    let active = true;
    const to = Date.now();
    const from = rangePoints[0]
      ? new Date(rangePoints[0].timestamp).getTime()
      : to - 30 * 86400000;
    let unsubscribe = () => {};

    benchmarkDatafeed
      .getBars(selectedBenchmark.symbol, from, to)
      .then((points) => {
        if (!active) return;
        setBenchmarkPoints(points);
        unsubscribe = benchmarkDatafeed.subscribeBars(
          selectedBenchmark.symbol!,
          (point) => {
            if (active) {
              setBenchmarkPoints((previous) => [...previous, point].slice(-10000));
            }
          }
        );
      })
      .catch((error: unknown) => {
        if (active) {
          console.error("Unable to load benchmark data.", error);
          setBenchmarkPoints([]);
        }
      });

    return () => {
      active = false;
      unsubscribe();
    };
  }, [benchmark, benchmarkDatafeed, period, useBenchmarkMock]);

  const compareBase = baseline;
  const benchmarkBase = nearestBenchmarkPoint(
    benchmarkPoints,
    sampledPoints[0] ? new Date(sampledPoints[0].timestamp).getTime() : Date.now()
  )?.value;
  const displayMode: DisplayMode =
    benchmarkPoints.length > 0 && hasInitialCapital ? "percent" : valueMode;

  const chartRows = useMemo(() => {
    const rows: ChartRow[] = [];
    if (!hasInitialCapital) return rows;

    for (const point of sampledPoints) {
      const timestamp = new Date(point.timestamp).getTime();
      if (!Number.isFinite(timestamp)) continue;
      rows.push({
        timestamp,
        equity: point.equity,
        balance: point.balance,
        timeWeightedEquity: point.timeWeightedEquity,
        timeWeightedBalance: point.timeWeightedBalance,
        timeWeightedReturn: point.timeWeightedReturn,
        underwater: point.underwater,
        cycle: point.cycle,
        openPositions: point.open_positions,
      });
    }

    if (rows.length === 0) {
      const now = Date.now();
      return [
        {
          timestamp: now - 60000,
          equity: baseline,
          balance: baseline,
          timeWeightedEquity: baseline,
          timeWeightedBalance: baseline,
          timeWeightedReturn: 0,
          underwater: 0,
          cycle: 0,
          openPositions: 0,
          placeholder: true,
        },
        {
          timestamp: now,
          equity: baseline,
          balance: baseline,
          timeWeightedEquity: baseline,
          timeWeightedBalance: baseline,
          timeWeightedReturn: 0,
          underwater: 0,
          cycle: 0,
          openPositions: 0,
          placeholder: true,
        },
      ];
    }

    if (rows.length === 1) {
      rows.push({
        ...rows[0],
        timestamp: rows[0].timestamp + 1000,
        placeholder: true,
      });
    }
    return rows;
  }, [sampledPoints, baseline, hasInitialCapital]);

  const chartData = useMemo(
    () => chartRows.map((row) => {
      const benchmarkAtPoint = nearestBenchmarkPoint(benchmarkPoints, row.timestamp);
      return {
        ...row,
        equityValue: displayMode === "usd" ? row.equity : row.timeWeightedReturn,
        balanceValue: displayMode === "usd"
          ? row.balance
          : (row.timeWeightedBalance / compareBase - 1) * 100,
        benchmarkValue:
          benchmarkBase && benchmarkAtPoint
            ? ((benchmarkAtPoint.value / benchmarkBase) - 1) * 100
            : null,
      };
    }),
    [chartRows, displayMode, compareBase, benchmarkPoints, benchmarkBase]
  );
  const equityDomain = useMemo(
    () =>
      displayMode === "usd"
        ? getEquityDomain(
            [
              baseline,
              ...chartData.flatMap((point) => [point.equityValue, point.balanceValue]),
            ],
            baseline
          )
        : getPercentDomain([
            0,
            ...chartData.flatMap((point) => [
              point.equityValue,
              point.balanceValue,
              ...(point.benchmarkValue == null ? [] : [point.benchmarkValue]),
            ]),
          ]),
    [displayMode, baseline, chartData]
  );

  const tradeMarkers = useMemo(() => {
    return trades.flatMap((trade) => {
      const events = trade.status === "closed"
        ? [
            { time: trade.entry_time, type: "Entry", pnl: null },
            { time: trade.exit_time, type: "Exit", pnl: trade.pnl },
          ]
        : [{ time: trade.entry_time, type: "Entry", pnl: trade.pnl }];

      return events.flatMap((event) => {
        const time = new Date(event.time ?? "").getTime();
        if (!Number.isFinite(time) || chartData.length === 0) return [];

        let nearest = chartData[0];
        for (const point of chartData) {
          if (Math.abs(point.timestamp - time) < Math.abs(nearest.timestamp - time)) {
            nearest = point;
          }
        }
        if (Math.abs(nearest.timestamp - time) > 5 * 60 * 1000) return [];

        return [{
          ...nearest,
          x: nearest.timestamp,
          y: nearest.equityValue,
          tradeSymbol: trade.symbol,
          tradeAction: trade.action,
          tradeEvent: event.type,
          tradePnl: event.pnl,
        }];
      });
    });
  }, [trades, chartData]);
  const capitalFlowMarkers = useMemo(
    () => capitalFlows.flatMap((flow) => {
      const timestamp = new Date(flow.timestamp).getTime();
      if (!Number.isFinite(timestamp) || chartData.length === 0) return [];
      const nearest = chartData.reduce((current, point) =>
        Math.abs(point.timestamp - timestamp) < Math.abs(current.timestamp - timestamp)
          ? point
          : current
      );
      return [{
        ...nearest,
        x: nearest.timestamp,
        y: nearest.equityValue,
        flowAmount: flow.amount,
      }];
    }),
    [capitalFlows, chartData]
  );

  updateChartHoverRef.current = (clientX, _clientY) => {
    const container = chartContainerRef.current;
    if (!container || !hasInitialCapital) {
      setChartHover(null);
      return;
    }
    const bounds = container.getBoundingClientRect();
    const plotElement = container.querySelector<SVGGElement>(".recharts-cartesian-grid");
    const plotBounds = plotElement?.getBoundingClientRect();
    const plotLeft = plotBounds ? plotBounds.left - bounds.left : 76;
    const plotTop = plotBounds ? plotBounds.top - bounds.top : 10;
    const plotWidth = Math.max(1, plotBounds?.width ?? bounds.width - plotLeft - 10);
    const plotHeight = Math.max(1, plotBounds?.height ?? bounds.height - plotTop - 40);
    const ratio = Math.max(
      0,
      Math.min(1, (clientX - bounds.left - plotLeft) / plotWidth)
    );
    const realRows = chartRows.filter((row) => !row.placeholder);
    const cursorX = plotLeft + ratio * plotWidth;
    const firstTime = realRows[0]?.timestamp ?? Date.now() - 60000;
    const lastTime = realRows.length > 1
      ? realRows[realRows.length - 1].timestamp
      : realRows.length === 1
        ? firstTime + 60000
        : Date.now();
    const targetTime = realRows.length > 1
      ? firstTime + (lastTime - firstTime) * ratio
      : firstTime + ratio * Math.max(lastTime - firstTime, 1);
    let row: ChartRow;

    if (realRows.length <= 1) {
      row = {
        timestamp: targetTime,
        equity: baseline,
        balance: baseline,
        timeWeightedEquity: baseline,
        timeWeightedBalance: baseline,
        timeWeightedReturn: 0,
        underwater: 0,
        cycle: 0,
        openPositions: 0,
      };
    } else {
      let rightIndex = realRows.findIndex((point) => point.timestamp >= targetTime);
      if (rightIndex <= 0) rightIndex = Math.min(1, realRows.length - 1);
      if (rightIndex === -1) rightIndex = realRows.length - 1;
      const left = realRows[rightIndex - 1];
      const right = realRows[rightIndex];
      const span = right.timestamp - left.timestamp;
      const interpolation = span > 0
        ? Math.max(0, Math.min(1, (targetTime - left.timestamp) / span))
        : 0;
      row = interpolateChartRow(left, right, interpolation, targetTime);
      const marker = tradeMarkers.find(
        (point) => point.timestamp === left.timestamp || point.timestamp === right.timestamp
      );
      if (marker) {
        row = {
          ...row,
          timestamp: targetTime,
          tradeSymbol: marker.tradeSymbol,
          tradeAction: marker.tradeAction,
          tradeEvent: marker.tradeEvent,
          tradePnl: marker.tradePnl,
        };
      }
    }

    const tooltipWidth = Math.min(230, bounds.width - 16);
    const tooltipHeight = Math.min(220, bounds.height - 16);
    const markerX = cursorX;
    const markerValue = displayMode === "usd"
      ? row.equity
      : row.timeWeightedReturn;
    const markerY = plotTop + (
      (equityDomain[1] - markerValue) /
      (equityDomain[1] - equityDomain[0] || 1)
    ) * plotHeight;
    const tooltipLeft = markerX + tooltipWidth + 16 > bounds.width
      ? markerX - tooltipWidth - 12
      : markerX + 12;
    const left = Math.max(8, Math.min(tooltipLeft, bounds.width - tooltipWidth - 8));
    const top = Math.max(
      8,
      Math.min(markerY - tooltipHeight / 2, bounds.height - tooltipHeight - 8)
    );

    setChartHover({
      row,
      x: markerX,
      markerY,
      markerTop: plotTop,
      markerBottom: plotTop + plotHeight,
      maxHeight: tooltipHeight,
    });
    equityTooltipPositionRef.current = {
      x: bounds.left + left,
      y: bounds.top + top,
      anchor: false,
    };
  };

  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => {
      const pointer = lastPointerRef.current;
      if (pointer) updateChartHoverRef.current(pointer.x, pointer.y);
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      if (pointerFrameRef.current) cancelAnimationFrame(pointerFrameRef.current);
    };
  }, []);

  useEffect(() => {
    const pointer = lastPointerRef.current;
    if (pointer) updateChartHoverRef.current(pointer.x, pointer.y);
  }, [displayMode, chartData, equityDomain]);

  const noRangeData = rangePoints.length === 0 && equityPoints.length > 0;
  const isBenchmarkAvailable = benchmarkPoints.length > 0;
  const selectedBenchmarkLabel =
    BENCHMARKS.find((item) => item.key === benchmark)?.label ?? "None";
  const selectDemoFixture = (fixtureId: string) => {
    provider.selectFixture?.(fixtureId);
  };

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">
            <span>Vortech Markets</span>
            <span className="text-slate-700">/</span>
            <span className="text-emerald-300">GenX Terminal</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-100 md:text-3xl">
            Account overview
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Live account performance and execution activity
          </p>
        </div>
        <div
          className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-[11px] font-mono tracking-wider ${
            connected
              ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-300"
              : "border-amber-500/25 bg-amber-500/5 text-amber-300"
          }`}
          aria-live="polite"
        >
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-amber-400"}`} />
          {connected ? "LIVE" : "RECONNECTING"}
          {DemoAccountBanner && isDemonstration && <DemoAccountBanner />}
        </div>
      </header>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_260px]">
        <div className="min-w-0 rounded-lg border border-slate-800 bg-[#111723] p-4 md:p-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs text-slate-400">Current equity</p>
              <div className="mt-1 font-mono text-3xl font-semibold tabular-nums tracking-tight text-slate-50 md:text-4xl">
                {!hasInitialCapital
                  ? "No deposit yet"
                  : displayMode === "usd"
                    ? currency.format(currentEquity)
                    : formatSignedPercent(accountReturnPercent)}
              </div>
              {hasInitialCapital && (
                <div className={`mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs tabular-nums ${
                  periodChange >= 0 ? "text-emerald-300" : "text-rose-400"
                }`}>
                  <span>{displayMode === "usd"
                  ? formatSignedCurrency(periodChange)
                    : formatSignedPercent(periodChangePercent)}</span>
                  <span>{displayMode === "usd"
                    ? formatSignedPercent(periodChangePercent)
                  : formatSignedCurrency(periodChange)}</span>
                  <span className="text-slate-500">selected period</span>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3">
            {DemoAccountControls && isDemonstration && fixtureId && (
              <DemoAccountControls
                fixtureId={fixtureId}
                onSelect={selectDemoFixture}
              />
            )}
            <div className="inline-flex flex-wrap rounded-md border border-slate-800 p-0.5" role="group" aria-label="Chart period">
                {PERIODS.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    aria-label={`Show ${item.label} of account performance`}
                    aria-pressed={period === item.key}
                    onClick={() => setPeriod(item.key)}
                    className={`rounded px-2.5 py-1.5 text-[11px] font-mono ${
                      period === item.key
                        ? "bg-emerald-500/10 text-emerald-300"
                        : "text-slate-400 hover:text-slate-100"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              {hasInitialCapital && <div className="inline-flex rounded-md border border-slate-800 p-0.5" role="group" aria-label="Chart value format">
                {(["usd", "percent"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    aria-label={mode === "usd" ? "Display chart values in dollars" : "Display chart values in percentages"}
                    aria-pressed={displayMode === mode}
                    onClick={() => setValueMode(mode)}
                    className={`rounded px-2.5 py-1.5 text-[11px] font-mono ${
                      displayMode === mode
                        ? "bg-slate-800 text-slate-100"
                        : "text-slate-400 hover:text-slate-100"
                    }`}
                  >
                    {mode === "usd" ? "$" : "%"}
                  </button>
                ))}
              </div>}
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-4 border-t border-slate-800/80 pt-3 text-[10px] text-slate-400">
            <Legend color="bg-emerald-400" label="Equity" />
            <Legend color="bg-slate-300" label="Balance" />
            <Legend color="bg-amber-400" label="Trade" />
            {capitalFlows.length > 0 && <Legend color="bg-slate-300" label="Capital flow" />}
            {benchmarkPoints.length > 0 && <Legend color="bg-sky-300" label={selectedBenchmarkLabel} />}
            <span className="ml-auto flex flex-wrap items-center gap-x-2 font-mono text-slate-500">
              <span>{sampledPoints.length} points</span>
              {sampledPoints.length === 0 && (
                <span className="text-slate-500">
                  · {!hasInitialCapital
                    ? "No deposit yet"
                    : noRangeData
                    ? "No equity snapshots in this period"
                    : `Waiting for first cycle · Baseline ${currency.format(baseline)}`}
                </span>
              )}
            </span>
          </div>
          <div
            ref={chartContainerRef}
            className="relative mt-2 h-[280px] w-full md:h-[340px]"
            onPointerMove={(event) => {
              const pointer = {
                x: event.clientX,
                y: event.clientY,
              };
              lastPointerRef.current = pointer;
              pendingPointerRef.current = pointer;
              if (!pointerFrameRef.current) {
                pointerFrameRef.current = requestAnimationFrame(() => {
                  pointerFrameRef.current = 0;
                  const latestPointer = pendingPointerRef.current;
                  if (latestPointer) {
                    updateChartHoverRef.current(latestPointer.x, latestPointer.y);
                  }
                });
              }
            }}
            onPointerLeave={() => {
              lastPointerRef.current = null;
              pendingPointerRef.current = null;
              if (pointerFrameRef.current) {
                cancelAnimationFrame(pointerFrameRef.current);
                pointerFrameRef.current = 0;
              }
              equityTooltipPositionRef.current = null;
              drawdownTooltipPositionRef.current = null;
              setChartHover(null);
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} syncId="genx-account" margin={{ top: 10, right: 8, bottom: 0, left: 4 }}>
                <defs>
                  <linearGradient id="accountEquityFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10B981" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#1E293B" strokeDasharray="2 5" />
                <XAxis
                  dataKey="timestamp"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(value) => formatAxisTime(Number(value), period)}
                  stroke="#475569"
                  tick={{ fill: "#94A3B8", fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: "#1E293B" }}
                  minTickGap={34}
                />
                <YAxis
                  hide={!hasInitialCapital}
                  domain={equityDomain}
                  stroke="#475569"
                  tick={{ fill: "#94A3B8", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  width={displayMode === "usd"
                    ? Math.max(72, currency.format(baseline).length * 6 + 8)
                    : 72}
                  tickFormatter={(value) =>
                    displayMode === "usd"
                      ? currency.format(Number(value))
                      : `${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`
                  }
                />
                {hasInitialCapital && <ReferenceLine
                  y={displayMode === "usd" ? baseline : 0}
                  stroke="#64748B"
                  strokeDasharray="4 5"
                  label={{
                    value: displayMode === "percent"
                      ? "Start 0.00%"
                      : `Start ${currency.format(baseline)}`,
                    fill: "#94A3B8",
                    fontSize: 9,
                    position: "insideTopRight",
                  }}
                />}
                {sampledPoints.length >= 2 && <Area
                  type="linear"
                  dataKey="equityValue"
                  name="Equity"
                  stroke="#10B981"
                  strokeWidth={2}
                  fill="url(#accountEquityFill)"
                  dot={false}
                  activeDot={{ r: 4, fill: "#6EE7B7", stroke: "#0B0F17", strokeWidth: 2 }}
                  isAnimationActive={false}
                />}
                {sampledPoints.length >= 2 && <Line
                  type="linear"
                  dataKey="balanceValue"
                  name="Balance"
                  stroke="#CBD5E1"
                  strokeWidth={1.4}
                  dot={false}
                  activeDot={{ r: 3, fill: "#CBD5E1", stroke: "#0B0F17", strokeWidth: 2 }}
                  isAnimationActive={false}
                />}
                {sampledPoints.length >= 2 && benchmarkPoints.length > 0 && (
                  <Line
                    type="monotone"
                    dataKey="benchmarkValue"
                    name={selectedBenchmarkLabel}
                    stroke="#7DD3FC"
                    strokeWidth={1.5}
                    strokeDasharray="4 3"
                    dot={false}
                    connectNulls
                    activeDot={{ r: 3, fill: "#7DD3FC", stroke: "#0B0F17", strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                )}
                {sampledPoints.length >= 2 && tradeMarkers.length > 0 && (
                  <Scatter
                    name="Trade"
                    data={tradeMarkers}
                    dataKey="y"
                    fill="#FBBF24"
                    shape="circle"
                    isAnimationActive={false}
                  />
                )}
                {sampledPoints.length >= 2 && capitalFlowMarkers.length > 0 && (
                  <Scatter
                    name="Capital flow"
                    data={capitalFlowMarkers}
                    dataKey="y"
                    fill="#CBD5E1"
                    shape="square"
                    isAnimationActive={false}
                  />
                )}
                {sampledPoints.length >= 2 && (
                  <Brush
                    dataKey="timestamp"
                    height={18}
                    travellerWidth={6}
                    stroke="#10B981"
                    fill="#0B0F17"
                    tickFormatter={(value) => formatAxisTime(Number(value), period)}
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
            {chartHover && (
              <>
                <div
                  className="pointer-events-none absolute border-l border-dashed border-slate-500/50"
                  style={{
                    left: chartHover.x,
                    top: chartHover.markerTop,
                    height: chartHover.markerBottom - chartHover.markerTop,
                  }}
                />
                <div
                  className="pointer-events-none absolute z-10 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[#0B0F17] bg-emerald-300 shadow-[0_0_0_1px_rgba(16,185,129,0.7)]"
                  style={{ left: chartHover.x, top: chartHover.markerY }}
                />
              </>
            )}
            <SmoothFollowTooltip
              containerRef={chartContainerRef}
              targetRef={equityTooltipPositionRef}
              active={chartHover !== null}
              className="w-[230px] max-w-[calc(100%-16px)] overflow-auto rounded-md p-3 text-[10px]"
              maxHeight={chartHover?.maxHeight}
            >
              {chartHover && (
                <EquityTooltip
                  row={chartHover.row}
                  startEquity={baseline}
                  previous={sampledPoints}
                  currencyCode={accountCurrency ?? "USD"}
                />
              )}
            </SmoothFollowTooltip>
          </div>
          {benchmark !== "none" && (
            <p className="mt-1 text-[11px] text-slate-500" role="status">
              {benchmark === "vtgx" && !isBenchmarkAvailable
                ? "Available at listing"
                : isBenchmarkAvailable
                ? useBenchmarkMock
                  ? "Development mock data · returns from start"
                  : `${selectedBenchmarkLabel} · returns from start`
                : `${selectedBenchmarkLabel} data feed is not connected.`}
            </p>
          )}
        </div>

        <aside className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
          <Link
            href="/dashboard/vtgx"
            className="group rounded-lg border border-slate-800 bg-[#111723] p-4 hover:border-emerald-500/30"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">{TOKEN_CONFIG.name} ({TOKEN_CONFIG.symbol})</span>
              <span className="rounded border border-amber-500/25 px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider text-amber-300">
                Pre-launch
              </span>
            </div>
            <p className="mt-5 font-mono text-2xl font-semibold text-slate-100">—</p>
            <p className="mt-1 text-[11px] text-slate-500">Price not listed</p>
            <VtgxSparkline />
            <span className="mt-4 inline-block text-[11px] text-emerald-300 group-hover:text-emerald-200">
              Token information →
            </span>
          </Link>
          <div className="rounded-lg border border-slate-800 bg-[#111723] p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-medium text-slate-300">Execution status</h2>
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-amber-400"}`} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <SmallStat label="Cycle" value={String(latest?.cycle ?? 0)} />
              <SmallStat label="Open positions" value={String(latest?.open_positions ?? metrics.openTrades)} />
              <SmallStat label="Open trades" value={String(metrics.openTrades)} />
              <SmallStat label="Closed trades" value={String(metrics.closedTrades)} />
            </div>
            <p className="mt-4 border-t border-slate-800 pt-3 text-[10px] text-slate-500">
              {connected ? "Live telemetry stream active" : "Waiting for telemetry reconnection"}
            </p>
          </div>
        </aside>
      </section>

      <section aria-label="Account performance metrics" className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
        <Metric label="Total equity" value={hasInitialCapital ? currency.format(currentEquity) : "No deposit yet"} accent="text-emerald-300" />
        <Metric label="Realized PnL" value={formatSignedCurrency(metrics.realizedPnL)} accent={metrics.realizedPnL < 0 ? "text-rose-400" : "text-emerald-300"} />
        <Metric label="Win rate" value={`${metrics.winRate.toFixed(1)}%`} detail={`${metrics.closedTrades} closed`} />
        <Metric label="Max drawdown" value={hasInitialCapital ? `${metrics.maxDrawdown.toFixed(2)}%` : "N/A"} accent={metrics.maxDrawdown > 0 ? "text-rose-400" : "text-slate-100"} />
        <Metric label="Balance" value={hasInitialCapital ? currency.format(latest?.balance ?? baseline) : "No deposit yet"} />
        <Metric label="Open / closed" value={`${metrics.openTrades} / ${metrics.closedTrades}`} />
        <Metric
          label="Profit factor"
          value={metrics.profitFactor === null ? "N/A" : metrics.profitFactor.toFixed(2)}
          info="Gross profit divided by gross loss across closed trades."
        />
        <Metric
          label="Sharpe"
          value={!hasInitialCapital || metrics.tradeSharpe === null ? "N/A" : metrics.tradeSharpe.toFixed(2)}
          detail="Annualized daily returns"
          info="Annualized mean daily return divided by daily return volatility; shown after 30 daily returns or 30 closed trades."
        />
        <Metric
          label="Calmar"
          value={!hasInitialCapital || metrics.calmar === null ? "N/A" : metrics.calmar.toFixed(2)}
          detail="Annualized return / max drawdown"
          info="Annualized equity return divided by the maximum peak-to-trough drawdown."
        />
        <Metric
          label="Realized R:R"
          value={metrics.averageRiskReward === null ? "N/A" : `${metrics.averageRiskReward.toFixed(2)}:1`}
          info="Average realized winning trade divided by the average absolute losing trade."
        />
        <Metric
          label="Expectancy / trade"
          value={metrics.closedTrades > 0 ? formatSignedCurrency(metrics.expectancy) : "N/A"}
          info="Average realized profit or loss per closed trade."
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-lg border border-slate-800 bg-[#111723] p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-medium text-slate-100">Drawdown</h2>
              <p className="mt-1 text-[11px] text-slate-500">Underwater from the running equity high</p>
            </div>
            <span className="text-[10px] font-mono text-rose-300">{hasInitialCapital ? `${metrics.maxDrawdown.toFixed(2)}% max` : "N/A"}</span>
          </div>
          <div
            ref={drawdownChartRef}
            className="relative h-28 w-full"
            onPointerMove={(event) => {
              drawdownTooltipPositionRef.current = {
                x: event.clientX,
                y: event.clientY,
                anchor: true,
              };
            }}
            onPointerLeave={() => {
              drawdownTooltipPositionRef.current = null;
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} syncId="genx-account" margin={{ top: 4, right: 8, bottom: 0, left: 4 }}>
                <defs>
                  <linearGradient id="drawdownFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#F87171" stopOpacity={0.02} />
                    <stop offset="100%" stopColor="#F87171" stopOpacity={0.18} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="timestamp" type="number" scale="time" domain={["dataMin", "dataMax"]} hide />
                <YAxis domain={[(min: number) => Math.min(min, -0.5), 0]} hide />
                <Tooltip
                  cursor={{ stroke: "#64748B", strokeWidth: 1, strokeDasharray: "3 4" }}
                  content={
                    <DrawdownTooltip
                      containerRef={drawdownChartRef}
                      pointerRef={drawdownTooltipPositionRef}
                    />
                  }
                />
                <ReferenceLine y={0} stroke="#334155" />
                <Area
                  type="monotone"
                  dataKey="underwater"
                  name="Drawdown"
                  stroke="#F87171"
                  strokeWidth={1.5}
                  fill="url(#drawdownFill)"
                  dot={false}
                  activeDot={{ r: 3, fill: "#F87171", stroke: "#0B0F17", strokeWidth: 2 }}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#111723] p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-medium text-slate-100">Benchmark</h2>
              <p className="mt-1 text-[11px] text-slate-500">Optional comparison source</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-1" role="group" aria-label="Benchmark selection">
            {BENCHMARKS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                aria-label={`Use ${label} as the performance benchmark`}
                aria-pressed={benchmark === key}
                onClick={() => {
                  setBenchmarkPoints([]);
                  setBenchmark(key);
                }}
                className={`rounded border px-2.5 py-1.5 text-[10px] ${
                  benchmark === key
                    ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
                    : "border-slate-800 text-slate-400 hover:text-slate-100"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="mt-3 text-[10px] leading-relaxed text-slate-500">
            {benchmark === "vtgx" && !isBenchmarkAvailable
              ? "Available at listing"
              : "Equity and benchmark returns are measured from the same starting point."}
          </p>
          {process.env.NODE_ENV === "development" && benchmark !== "none" && benchmark !== "vtgx" && (
            <label className="mt-3 flex items-center gap-2 text-[10px] text-slate-500">
              <input
                type="checkbox"
                checked={useBenchmarkMock}
                onChange={(event) => setUseBenchmarkMock(event.target.checked)}
                className="accent-emerald-500"
              />
              Use development mock data
            </label>
          )}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <MonthlyHeatmap returns={monthlyReturns} />
        <RecentTrades trades={trades.slice(0, 6)} currencyCode={accountCurrency ?? "USD"} />
      </section>
    </div>
  );
}

function getPeriodCutoff(period: PeriodKey, now: number, oldest: number) {
  const day = 86400000;
  if (period === "1H") return now - 60 * 60 * 1000;
  if (period === "1D") return now - day;
  if (period === "1W") return now - 7 * day;
  if (period === "1M") return now - 30 * day;
  if (period === "3M") return now - 90 * day;
  if (period === "YTD") {
    const date = new Date(now);
    return Date.UTC(date.getUTCFullYear(), 0, 1);
  }
  return oldest;
}

function sampleEquityPoints<T extends { timestamp: string }>(
  range: T[],
  period: PeriodKey,
  allPoints: T[]
): T[] {
  const oldest = allPoints[0]
    ? new Date(allPoints[0].timestamp).getTime()
    : 0;
  const newest = allPoints[allPoints.length - 1]
    ? new Date(allPoints[allPoints.length - 1].timestamp).getTime()
    : oldest;
  const historyExceedsYear = newest - oldest > 365 * 86400000;
  const bucketSize =
    period === "1W"
      ? 60 * 60 * 1000
      : period === "1M" || period === "3M" || period === "YTD"
      ? 86400000
      : period === "ALL"
      ? historyExceedsYear
        ? 7 * 86400000
        : 86400000
      : null;

  if (bucketSize === null) return range;

  const buckets = new Map<number, (typeof range)[number]>();
  for (const point of range) {
    const timestamp = new Date(point.timestamp).getTime();
    if (!Number.isFinite(timestamp)) continue;
    buckets.set(Math.floor(timestamp / bucketSize) * bucketSize, point);
  }
  return Array.from(buckets.values());
}

function nearestBenchmarkPoint(points: BenchmarkPoint[], time: number) {
  if (points.length === 0) return undefined;
  let low = 0;
  let high = points.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (points[middle].time < time) low = middle + 1;
    else high = middle;
  }
  const before = points[Math.max(0, low - 1)];
  const after = points[Math.min(points.length - 1, low)];
  return Math.abs(before.time - time) <= Math.abs(after.time - time)
    ? before
    : after;
}

function interpolateChartRow(
  left: ChartRow,
  right: ChartRow,
  ratio: number,
  timestamp: number
): ChartRow {
  const interpolate = (start: number, end: number) =>
    start + (end - start) * ratio;
  const nearest = ratio < 0.5 ? left : right;

  return {
    timestamp,
    equity: interpolate(left.equity, right.equity),
    balance: interpolate(left.balance, right.balance),
    timeWeightedEquity: interpolate(left.timeWeightedEquity, right.timeWeightedEquity),
    timeWeightedBalance: interpolate(left.timeWeightedBalance, right.timeWeightedBalance),
    timeWeightedReturn: interpolate(left.timeWeightedReturn, right.timeWeightedReturn),
    underwater: interpolate(left.underwater, right.underwater),
    cycle: nearest.cycle,
    openPositions: Math.round(interpolate(left.openPositions, right.openPositions)),
    tradeSymbol: nearest.tradeSymbol,
    tradeAction: nearest.tradeAction,
    tradeEvent: nearest.tradeEvent,
    tradePnl: nearest.tradePnl,
  };
}

function formatAxisTime(timestamp: number, period: PeriodKey) {
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime())) return "";
  if (period === "1H") {
    return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }
  if (period === "1D") {
    return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function signedCurrency(value: number, currencyCode = "USD") {
  return `${value >= 0 ? "+" : "−"}${formatAccountCurrency(Math.abs(value), currencyCode)}`;
}

function formatAccountCurrency(value: number, currencyCode: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currencyCode,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatSignedPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {label}
    </span>
  );
}

function SmallStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-sm tabular-nums text-slate-200">{value}</div>
      <div className="mt-0.5 text-[10px] text-slate-500">{label}</div>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
  accent = "text-slate-100",
  info,
}: {
  label: string;
  value: string;
  detail?: string;
  accent?: string;
  info?: string;
}) {
  return (
    <div className="min-w-0 rounded-md border border-slate-800 bg-[#111723] px-3 py-3">
      <div className="flex items-center gap-1">
        <p className="truncate text-[10px] text-slate-500">{label}</p>
        {info && (
          <button
            type="button"
            title={info}
            aria-label={`${label}: ${info}`}
            className="inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-slate-600 text-[9px] leading-none text-slate-400 hover:border-slate-400 hover:text-slate-200"
          >
            i
          </button>
        )}
      </div>
      <p className={`mt-1 truncate font-mono text-sm font-medium tabular-nums ${accent}`}>{value}</p>
      {detail && <p className="mt-1 truncate text-[9px] text-slate-600">{detail}</p>}
    </div>
  );
}

function EquityTooltip({
  row,
  startEquity,
  previous,
  currencyCode,
}: {
  row: ChartRow;
  startEquity: number;
  previous: FlowAdjustedEquity[];
  currencyCode: string;
}) {
  const previousPoint = previous
    .filter((point) => new Date(point.timestamp).getTime() < row.timestamp)
    .at(-1);
  const change = row.timeWeightedEquity - startEquity;
  const changePercent = startEquity ? (change / startEquity) * 100 : 0;
  const previousAdjustedEquity = previousPoint?.timeWeightedEquity;
  const delta = previousAdjustedEquity
    ? row.timeWeightedEquity - previousAdjustedEquity
    : 0;
  const deltaPercent = previousAdjustedEquity
    ? (delta / previousAdjustedEquity) * 100
    : 0;
  const trade = row.tradeSymbol ? row : undefined;

  return (
    <>
      <p className="mb-2 border-b border-slate-800 pb-2 font-mono text-slate-400">
        {new Date(row.timestamp).toLocaleString("en-US")} · Cycle {row.cycle}
      </p>
      <TooltipRow label="Equity" value={formatAccountCurrency(row.equity, currencyCode)} color="text-emerald-300" />
      <TooltipRow label="Balance" value={formatAccountCurrency(row.balance, currencyCode)} color="text-slate-200" />
      <TooltipRow label="Positions" value={String(row.openPositions)} color="text-amber-300" />
      <TooltipRow label="Drawdown" value={`${row.underwater.toFixed(2)}%`} color="text-rose-400" />
      <TooltipRow label="Vs. start" value={`${signedCurrency(change, currencyCode)} (${changePercent >= 0 ? "+" : ""}${changePercent.toFixed(2)}%)`} color={change >= 0 ? "text-emerald-300" : "text-rose-400"} />
      {previousPoint && <TooltipRow label="Vs. previous" value={`${signedCurrency(delta, currencyCode)} (${deltaPercent >= 0 ? "+" : ""}${deltaPercent.toFixed(2)}%)`} color={delta >= 0 ? "text-emerald-300" : "text-rose-400"} />}
      {trade?.tradeSymbol && (
        <div className="mt-2 border-t border-slate-800 pt-2">
          <TooltipRow
            label={`${trade.tradeSymbol} ${trade.tradeAction ?? ""} ${trade.tradeEvent ?? ""}`}
            value={trade.tradePnl == null ? "—" : signedCurrency(trade.tradePnl, currencyCode)}
            color={trade.tradePnl == null ? "text-amber-300" : trade.tradePnl >= 0 ? "text-emerald-300" : "text-rose-400"}
          />
        </div>
      )}
    </>
  );
}

function DrawdownTooltip({
  active,
  payload,
  containerRef,
  pointerRef,
}: {
  active?: boolean;
  payload?: Array<{ payload?: ChartRow }>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  pointerRef: TooltipPositionRef;
}) {
  const rowRef = useRef<ChartRow | null>(null);
  if (active && payload?.length) {
    const nextRow = payload.find((entry) => entry.payload && "underwater" in entry.payload)?.payload;
    if (nextRow && !nextRow.placeholder) rowRef.current = nextRow;
  }
  const row = rowRef.current;
  const container = containerRef.current;
  if (!container) return null;
  return (
    createPortal(
      <SmoothFollowTooltip
        containerRef={containerRef}
        targetRef={pointerRef}
        active={Boolean(active && row)}
        className="whitespace-nowrap rounded-md px-3 py-2 text-[10px] font-mono"
      >
        {row && (
          <>
            <span className="text-slate-200">{new Date(row.timestamp).toLocaleString("en-US")} · </span>
            <span className="text-rose-300">Drawdown {row.underwater.toFixed(2)}%</span>
          </>
        )}
      </SmoothFollowTooltip>,
      container
    )
  );
}

function TooltipRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-0.5">
      <span className="text-slate-400">{label}</span>
      <span className={`text-right font-mono tabular-nums ${color}`}>{value}</span>
    </div>
  );
}

export function RecentTrades({
  trades,
  currencyCode,
}: {
  trades: LiveTrade[];
  currencyCode: string;
}) {
  return (
    <section className="rounded-lg border border-slate-800 bg-[#111723] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-slate-100">Recent executions</h2>
          <p className="mt-1 text-[11px] text-slate-500">Latest engine activity</p>
        </div>
        <Link href="/dashboard/trades" className="text-[10px] text-emerald-300 hover:text-emerald-200">
          View all →
        </Link>
      </div>
      {trades.length === 0 ? (
        <p className="py-5 text-center text-[11px] text-slate-500">Waiting for trades from the live engine.</p>
      ) : (
        <div className="space-y-1">
          {trades.map((trade) => (
            <div key={trade.ticket} className="flex items-center justify-between gap-3 border-t border-slate-800/70 py-2.5">
              <div className="flex min-w-0 items-center gap-2">
                <span className={`w-9 shrink-0 rounded border px-1 py-0.5 text-center text-[8px] font-mono ${
                  trade.action === "BUY"
                    ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-300"
                    : "border-slate-700 text-slate-300"
                }`}>
                  {trade.action}
                </span>
                <span className="truncate font-mono text-[11px] text-slate-200">{trade.symbol}</span>
              </div>
              <span className={`shrink-0 font-mono text-[10px] tabular-nums ${
                trade.status === "open"
                  ? "text-amber-300"
                  : (trade.pnl ?? 0) < 0
                  ? "text-rose-400"
                  : "text-emerald-300"
              }`}>
                {trade.status === "open" ? "OPEN" : signedCurrency(trade.pnl ?? 0, currencyCode)}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
