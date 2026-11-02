"use client";

import { useEffect, useState } from "react";
import {
  type MarketDataProvider,
  type VtgxBar,
} from "@/lib/vtgxDatafeed";
import { createMarketDataProvider } from "@/lib/marketDataProviderFactory";
import { TOKEN_CONFIG } from "@/lib/tokenConfig";

export default function VtgxSparkline() {
  const [provider, setProvider] = useState<MarketDataProvider | null>(null);
  const [bars, setBars] = useState<VtgxBar[]>([]);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [change24h, setChange24h] = useState<{ value: number; percent: number } | null>(null);

  useEffect(() => {
    let active = true;
    createMarketDataProvider()
      .then((marketProvider) => {
        if (active) setProvider(marketProvider);
      })
      .catch((error: unknown) => {
        console.error(`Unable to initialize ${TOKEN_CONFIG.ticker} market data.`, error);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!provider) return;
    let active = true;
    let unsubscribe = () => {};
    const to = Math.floor(Date.now() / 1000);
    provider
      .getBars(
        "1H",
        (to - 28 * 60 * 60) as VtgxBar["time"],
        to as VtgxBar["time"]
      )
      .then(async (result) => {
        if (!active) return;
        setBars(result.sort((a, b) => Number(a.time) - Number(b.time)));
        unsubscribe = provider.subscribeBars("1H", (bar) => {
          if (!active) return;
          setBars((current) => {
            const index = current.findIndex((item) => item.time === bar.time);
            if (index === -1) return [...current, bar];
            return current.map((item, itemIndex) => itemIndex === index ? bar : item);
          });
          provider.getLastPrice().then((value) => {
            if (active) setLastPrice(value);
          }).catch((error: unknown) => {
            console.error(`Unable to update ${TOKEN_CONFIG.ticker} price.`, error);
          });
          provider.get24hChange().then((value) => {
            if (active) setChange24h(value);
          }).catch((error: unknown) => {
            console.error(`Unable to update ${TOKEN_CONFIG.ticker} 24-hour change.`, error);
          });
        });
        const [price, change] = await Promise.all([
          provider.getLastPrice(),
          provider.get24hChange(),
        ]);
        if (active) {
          setLastPrice(price);
          setChange24h(change);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          console.error(`Unable to load ${TOKEN_CONFIG.ticker} 24-hour sparkline.`, error);
        }
      });

    return () => {
      active = false;
      unsubscribe();
    };
  }, [provider]);

  const values = bars.map((bar) => bar.close);
  const last = lastPrice ?? values[values.length - 1];
  const changeValue = change24h?.value ?? null;
  const change = change24h?.percent ?? null;
  const points = values.length > 1
    ? values.map((value, index) => {
        const min = Math.min(...values);
        const max = Math.max(...values);
        const range = max - min || Math.abs(max) * 0.005 || 1;
        const x = (index / (values.length - 1)) * 100;
        const y = 30 - ((value - min) / range) * 26;
        return `${x},${y}`;
      }).join(" ")
    : "";

  return (
    <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-800 pt-3">
      <div>
        <p className="text-[10px] text-slate-500">24h price movement</p>
        {last == null ? (
          <p className="mt-1 font-mono text-xs text-slate-400">Available at listing</p>
        ) : (
          <>
            <p className="mt-1 font-mono text-[10px] text-slate-500">{TOKEN_CONFIG.name} ({TOKEN_CONFIG.symbol})</p>
            <p className="mt-1 font-mono text-xs tabular-nums text-slate-200">
              {last.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 6 })}
            </p>
            <p className={`mt-0.5 font-mono text-[10px] tabular-nums ${
              (change ?? 0) < 0 ? "text-rose-400" : "text-emerald-300"
            }`}>
              {change != null && changeValue != null
                ? `${changeValue >= 0 ? "+" : "−"}${Math.abs(changeValue).toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 6 })} (${change >= 0 ? "+" : ""}${change.toFixed(2)}%)`
                : "—"}
            </p>
          </>
        )}
      </div>
      {points && (
        <svg
          viewBox="0 0 100 32"
          preserveAspectRatio="none"
          role="img"
          aria-label={`${TOKEN_CONFIG.name} 24-hour sparkline, ${change?.toFixed(2)} percent change`}
          className="h-8 w-24"
        >
          <polyline
            points={points}
            fill="none"
            stroke="#10B981"
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      )}
    </div>
  );
}
