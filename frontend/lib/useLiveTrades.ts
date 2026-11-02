"use client";

import { useEffect, useRef, useState } from "react";

export type LiveTrade = {
  ticket: number;
  session_id: string;
  strategy: string;
  symbol: string;
  action: string;
  entry_price: number | null;
  exit_price: number | null;
  lot: number;
  sl: number | null;
  tp: number | null;
  pnl: number | null;
  status: "open" | "closed";
  entry_time: string | null;
  exit_time: string | null;
  regime?: string;
};

export type LiveEquity = {
  session_id: string;
  equity: number;
  balance: number;
  open_positions: number;
  cycle: number;
  timestamp: string;
  /** Supplied by the backend as the account's first deposit or opening balance. */
  initial_capital?: number | null;
};

export type CapitalFlow = {
  timestamp: string;
  /** Signed amount: deposits are positive and withdrawals are negative. */
  amount: number;
};

// The websocket API must provide initial_capital and forward capital_flow events with timestamp and signed amount.
export function useLiveTrades(maxTrades = 200, maxEquityPoints = 300, enabled = true) {
  const [trades, setTrades] = useState<LiveTrade[]>([]);
  const [equityPoints, setEquityPoints] = useState<LiveEquity[]>([]);
  const [initialCapital, setInitialCapital] = useState<number | null>(null);
  const [currency, setCurrency] = useState<string | null>(null);
  const [capitalFlows, setCapitalFlows] = useState<CapitalFlow[]>([]);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const pendingEquityRef = useRef<LiveEquity[]>([]);

  useEffect(() => {
    if (typeof window === "undefined" || !enabled) return;

    const API_BASE =
      process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    const wsUrl = API_BASE.replace(/^http/, "ws") + "/ws/live";

    let reconnectTimer: any;
    let equityFlushTimer: ReturnType<typeof setTimeout> | undefined;
    let shouldReconnect = true;

    function flushEquityPoints() {
      equityFlushTimer = undefined;
      const pending = pendingEquityRef.current;
      pendingEquityRef.current = [];
      if (pending.length === 0) return;

      setEquityPoints((previous) => [...previous, ...pending].slice(-maxEquityPoints));
    }

    function connect() {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log("[ws] connected");
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "trade_open") {
            const d = msg.data;
            const trade: LiveTrade = {
              ticket: d.ticket,
              session_id: msg.session_id,
              strategy: d.strategy || "",
              symbol: d.symbol || "",
              action: d.action || "",
              entry_price: d.entry_price ?? null,
              exit_price: null,
              lot: d.lot ?? 0,
              sl: d.sl ?? null,
              tp: d.tp ?? null,
              pnl: null,
              status: "open",
              entry_time: msg.timestamp ?? null,
              exit_time: null,
              regime: d.regime,
            };
            setTrades((prev) => {
              const updated = [trade, ...prev];
              return updated.slice(0, maxTrades);
            });
          } else if (msg.type === "trade_close") {
            const d = msg.data;
            // Find the open trade and mark it closed
            setTrades((prev) =>
              prev.map((t) =>
                t.ticket === d.ticket
                  ? {
                      ...t,
                      exit_price: d.exit_price ?? null,
                      pnl: d.pnl ?? 0,
                      status: "closed",
                      exit_time: msg.timestamp ?? null,
                    }
                  : t
              )
            );
          } else if (msg.type === "equity") {
            const d = msg.data;
            // The websocket API must include initial_capital here for a valid Overview baseline.
            const capital = d.initial_capital ?? d.initialCapital;
            const accountCurrency = d.account_currency ?? d.currency;
            if (typeof capital === "number" && Number.isFinite(capital)) {
              setInitialCapital(capital);
            }
            if (typeof accountCurrency === "string" && accountCurrency.length > 0) {
              setCurrency(accountCurrency);
            }
            const point: LiveEquity = {
              session_id: msg.session_id,
              equity: d.equity ?? 0,
              balance: d.balance ?? 0,
              open_positions: d.open_positions ?? 0,
              cycle: d.cycle ?? 0,
              timestamp: msg.timestamp ?? new Date().toISOString(),
              initial_capital:
                typeof capital === "number" && Number.isFinite(capital)
                  ? capital
                  : undefined,
            };
            pendingEquityRef.current.push(point);
            if (equityFlushTimer === undefined) {
              equityFlushTimer = setTimeout(flushEquityPoints, 250);
            }
          } else if (msg.type === "capital_flow") {
            // The backend watcher must forward capital_flow events with timestamp and signed amount.
            const flow = msg.data;
            const amount = Number(flow?.amount);
            const timestamp = msg.timestamp ?? flow?.timestamp;
            if (Number.isFinite(amount) && typeof timestamp === "string") {
              setCapitalFlows((previous) =>
                [...previous, { timestamp, amount }].slice(-maxEquityPoints)
              );
            }
          }
        } catch (e) {
          console.warn("[ws] parse error:", e);
        }
      };

      ws.onerror = () => console.warn("[ws] error");
      ws.onclose = () => {
        console.log("[ws] closed");
        setConnected(false);
        if (shouldReconnect) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };
    }

    connect();

    return () => {
      shouldReconnect = false;
      clearTimeout(reconnectTimer);
      if (equityFlushTimer !== undefined) clearTimeout(equityFlushTimer);
      pendingEquityRef.current = [];
      socketRef.current?.close();
    };
  }, [maxTrades, maxEquityPoints, enabled]);

  return { trades, equityPoints, initialCapital, currency, capitalFlows, connected };
}