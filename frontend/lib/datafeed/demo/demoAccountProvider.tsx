"use client";

import { useMemo } from "react";
import type {
  AccountDataProvider,
  AccountDataSnapshot,
} from "@/lib/accountDataProvider";
import type { CapitalFlow, LiveEquity, LiveTrade } from "@/lib/useLiveTrades";

const FIXTURES = [
  { id: "500", label: "500 $" },
  { id: "100000", label: "100,000 $" },
  { id: "2500000", label: "2,500,000 $" },
  { id: "empty", label: "Empty account" },
] as const;

type FixtureId = (typeof FIXTURES)[number]["id"];

const DAY_MS = 86400000;
const DEMO_DAYS = 90;
const DEMO_BASE_CAPITAL = 100000;

export function createDemoAccountProvider(initialFixture = "100000"): AccountDataProvider {
  let snapshot = createSnapshot(normalizeFixtureId(initialFixture));
  const listeners = new Set<() => void>();
  let tick = 0;

  const timer = setInterval(() => {
    if (snapshot.initialCapital === null || snapshot.equityPoints.length === 0) return;
    tick += 1;
    const previous = snapshot.equityPoints[snapshot.equityPoints.length - 1];
    const time = Date.now();
    const perturbation = Math.sin(tick * 1.73) * 0.00008 + Math.cos(tick * 0.47) * 0.00004;
    const balance = previous.balance * (1 + perturbation);
    const equity = balance * (1 + Math.sin(tick * 0.31) * 0.0002);
    const point: LiveEquity = {
      ...previous,
      equity,
      balance,
      cycle: previous.cycle + 1,
      timestamp: new Date(time).toISOString(),
    };
    snapshot = { ...snapshot, equityPoints: [...snapshot.equityPoints.slice(-9999), point] };
    listeners.forEach((listener) => listener());
  }, 5000);

  return {
    getSnapshot: () => snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    selectFixture(fixtureId) {
      snapshot = createSnapshot(normalizeFixtureId(fixtureId));
      tick = 0;
      listeners.forEach((listener) => listener());
    },
    dispose() {
      clearInterval(timer);
      listeners.clear();
    },
  };
}

export function DemoAccountControls({
  fixtureId,
  onSelect,
}: {
  fixtureId: string;
  onSelect: (fixtureId: string) => void;
}) {
  const selected = FIXTURES.some((fixture) => fixture.id === fixtureId)
    ? fixtureId
    : "empty";
  return (
    <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Demo account fixture">
      {FIXTURES.map((fixture) => (
        <button
          key={fixture.id}
          type="button"
          aria-pressed={selected === fixture.id}
          onClick={() => onSelect(fixture.id)}
          className={`rounded border px-2 py-1 text-[9px] font-mono ${
            selected === fixture.id
              ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-300"
              : "border-slate-800 text-slate-500 hover:text-slate-300"
          }`}
        >
          {fixture.label}
        </button>
      ))}
    </div>
  );
}

export function DemoAccountBanner() {
  return (
    <span className="rounded border border-amber-500/20 bg-amber-500/5 px-2 py-1 text-[9px] font-mono uppercase tracking-wider text-amber-300">
      Demo data
    </span>
  );
}

function normalizeFixtureId(fixtureId: string): FixtureId {
  return FIXTURES.some((fixture) => fixture.id === fixtureId)
    ? (fixtureId as FixtureId)
    : "100000";
}

function createSnapshot(fixtureId: FixtureId): AccountDataSnapshot {
  if (fixtureId === "empty") {
    return {
      initialCapital: null,
      currency: "USD",
      equityPoints: [],
      trades: [],
      capitalFlows: [],
      connected: true,
      isDemonstration: true,
      fixtureId,
    };
  }

  const initialCapital = Number(fixtureId);
  const scale = initialCapital / DEMO_BASE_CAPITAL;
  const now = Date.now();
  const start = now - DEMO_DAYS * DAY_MS;
  const flows: CapitalFlow[] = [
    { timestamp: new Date(start + 31 * DAY_MS).toISOString(), amount: 12500 * scale },
    { timestamp: new Date(start + 62 * DAY_MS).toISOString(), amount: -4500 * scale },
  ];
  const equityPoints = createHistory(start, now, initialCapital, flows, fixtureId);
  const trades = createTrades(start, now, scale);

  return {
    initialCapital,
    currency: "USD",
    equityPoints,
    trades,
    capitalFlows: flows,
    connected: true,
    isDemonstration: true,
    fixtureId,
  };
}

function createHistory(
  start: number,
  end: number,
  initialCapital: number,
  flows: CapitalFlow[],
  fixtureId: string
): LiveEquity[] {
  const random = seededRandom(Number(fixtureId) ^ 0x73a2f19b);
  const points: LiveEquity[] = [];
  const interval = 5 * 60 * 1000;
  const flowEvents = new Map(
    flows.map((flow) => [new Date(flow.timestamp).getTime(), flow.amount])
  );
  let performanceValue = initialCapital;
  let depositedCapital = initialCapital;
  let price = initialCapital;
  let regime = 0;
  let regimeRemaining = 0;
  let cycle = 0;

  for (let time = start; time <= end; time += interval) {
    if (time > start) {
      if (regimeRemaining <= 0) {
        regime = Math.floor(random() * 3);
        regimeRemaining = Math.floor(30 + random() * 210);
      }
      regimeRemaining -= 1;
      const drift = regime === 0 ? 0.00015 : regime === 1 ? -0.00018 : 0;
      const volatility = regime === 2 ? 0.0018 : 0.0027;
      const randomMove = (random() + random() + random() - 1.5) * volatility;
      const shock = random() < 0.012 ? (random() - 0.58) * 0.012 : 0;
      performanceValue = Math.max(
        initialCapital * 0.58,
        performanceValue * (1 + drift + randomMove + shock)
      );
    }

    for (const [flowTime, amount] of flowEvents) {
      if (flowTime > time - interval && flowTime <= time) depositedCapital += amount;
    }
    price = performanceValue + (depositedCapital - initialCapital);
    const floatingPnl = Math.sin(cycle * 0.19) * initialCapital * 0.0018;
    cycle += 1;
    points.push({
      session_id: "demo-account",
      equity: Math.max(0, price + floatingPnl),
      balance: Math.max(0, price),
      open_positions: cycle % 17 < 5 ? 1 : 0,
      cycle,
      timestamp: new Date(time).toISOString(),
      initial_capital: initialCapital,
    });
  }

  return points;
}

function createTrades(start: number, end: number, scale: number): LiveTrade[] {
  const random = seededRandom(0x11ea57);
  return Array.from({ length: 20 }, (_, index) => {
    const entryTime = start + ((index + 1) / 21) * (end - start);
    const isOpen = index >= 16;
    const pnl = (random() < 0.61 ? 1 : -1) * (220 + random() * 1450) * scale;
    return {
      ticket: 71000 + index,
      session_id: "demo-account",
      strategy: ["Momentum", "Mean Reversion", "Breakout"][index % 3],
      symbol: ["EURUSD", "XAUUSD", "BTCUSD", "GBPUSD"][index % 4],
      action: index % 2 === 0 ? "BUY" : "SELL",
      entry_price: 1.08 + random() * 0.12,
      exit_price: isOpen ? null : 1.08 + random() * 0.12,
      lot: 0.1 + random() * 0.9,
      sl: null,
      tp: null,
      pnl: isOpen ? null : pnl,
      status: isOpen ? "open" : "closed",
      entry_time: new Date(entryTime).toISOString(),
      exit_time: isOpen
        ? null
        : new Date(Math.min(end, entryTime + (1 + random() * 30) * 3600000)).toISOString(),
      regime: ["trend", "range", "volatility"][index % 3],
    };
  });
}

function seededRandom(seed: number) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}
