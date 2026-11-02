"use client";

import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  createChart,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  PriceScaleMode,
  type IChartApi,
  type MouseEventParams,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type {
  MarketDataProvider,
  VtgxBar,
  VtgxTimeframe,
} from "@/lib/vtgxDatafeed";
import { alignUtcTime, TIMEFRAME_SECONDS } from "@/lib/vtgxDatafeed";
import { TOKEN_CONFIG } from "@/lib/tokenConfig";

type HoverBar = VtgxBar | null;

export default function VtgxCandlestickChart({
  provider,
  timeframe,
  logarithmic,
  simulated,
  chartType,
  showVolume = true,
}: {
  provider: MarketDataProvider | null;
  timeframe: VtgxTimeframe;
  logarithmic: boolean;
  simulated: boolean;
  chartType: "candles" | "line";
  showVolume?: boolean;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const verticalCrosshairRef = useRef<HTMLDivElement>(null);
  const horizontalCrosshairRef = useRef<HTMLDivElement>(null);
  const snapMarkerRef = useRef<HTMLDivElement>(null);
  const priceLabelRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const subscriptionCleanupRef = useRef<() => void>(() => {});
  const subscriptionIdRef = useRef(0);
  const [hoverBar, setHoverBar] = useState<HoverBar>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [change24h, setChange24h] = useState<{ value: number; percent: number } | null>(null);
  const [hasBars, setHasBars] = useState(false);
  const [feedError, setFeedError] = useState<string | null>(null);

  const candleChange = hoverBar ? hoverBar.close - hoverBar.open : 0;
  const candleChangePercent =
    hoverBar?.open ? (candleChange / hoverBar.open) * 100 : null;

  useEffect(() => {
    subscriptionCleanupRef.current();
    subscriptionCleanupRef.current = () => {};
    const subscriptionId = ++subscriptionIdRef.current;
    const host = hostRef.current;
    if (!host || !provider) return;

    setFeedError(null);
    setHasBars(false);
    setHoverBar(null);
    setLastPrice(null);
    setChange24h(null);

    const chart = createChart(host, {
      width: host.clientWidth,
      height: 350,
      layout: {
        background: { color: "#111723" },
        textColor: "#94A3B8",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "rgba(30, 41, 59, 0.55)" },
        horzLines: { color: "rgba(30, 41, 59, 0.75)" },
      },
      rightPriceScale: { borderColor: "#1E293B", minimumWidth: 64 },
      timeScale: {
        borderColor: "#1E293B",
        timeVisible: timeframe !== "1D",
        secondsVisible: false,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(148, 163, 184, 0.38)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#1E293B",
          visible: false,
          labelVisible: false,
        },
        horzLine: {
          color: "rgba(148, 163, 184, 0.38)",
          width: 1,
          style: 2,
          labelBackgroundColor: "#1E293B",
          visible: false,
          labelVisible: false,
        },
      },
      handleScroll: true,
      handleScale: true,
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10B981",
      downColor: "#F87171",
      borderUpColor: "#10B981",
      borderDownColor: "#F87171",
      wickUpColor: "#34D399",
      wickDownColor: "#F87171",
      priceLineColor: "#10B981",
      lastValueVisible: true,
      visible: chartType === "candles",
    });
    const lineSeries = chart.addSeries(LineSeries, {
      color: "#10B981",
      lineWidth: 2,
      priceLineColor: "#10B981",
      lastValueVisible: true,
      crosshairMarkerVisible: false,
      visible: chartType === "line",
    });
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      lastValueVisible: false,
      priceLineVisible: false,
      visible: showVolume,
    });
    chart.priceScale("right").applyOptions({
      mode: logarithmic ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      scaleMargins: { top: 0.08, bottom: 0.24 },
      minimumWidth: 64,
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      visible: false,
    });

    const barsByTime = new Map<number, VtgxBar>();
    let orderedBars: VtgxBar[] = [];
    let seriesReady = false;
    let lastCandleTime: number | null = null;
    let lastLineTime: number | null = null;
    let lastVolumeTime: number | null = null;
    const pendingBars = new Map<number, VtgxBar>();
    let previousSnap: { time: number; price: number; level: string } | null = null;
    let pointer: { x: number; y: number } | null = null;
    let lastCrosshairParam: MouseEventParams<Time> | null = null;
    let target: { x: number; y: number; price: number | null; snapped: boolean } | null = null;
    let displayed: { x: number; y: number } | null = null;
    let animationFrame = 0;
    let lastFrameTime = 0;

    const hideCrosshair = () => {
      if (overlayRef.current) overlayRef.current.style.opacity = "0";
      target = null;
      pointer = null;
      previousSnap = null;
    };

    const updateOverlay = (x: number, y: number, price: number | null, snapped: boolean) => {
      const overlay = overlayRef.current;
      const vertical = verticalCrosshairRef.current;
      const horizontal = horizontalCrosshairRef.current;
      const marker = snapMarkerRef.current;
      const label = priceLabelRef.current;
      if (!overlay || !vertical || !horizontal || !marker || !label) return;

      const paneWidth = chart.timeScale().width();
      const paneHeight = host.clientHeight - chart.timeScale().height();
      const axisWidth = chart.priceScale("right").width();
      const labelWidth = Math.max(64, axisWidth);
      const boundedX = Math.max(0, Math.min(paneWidth, x));
      const boundedY = Math.max(0, Math.min(paneHeight, y));
      overlay.style.opacity = "1";
      vertical.style.left = `${boundedX}px`;
      vertical.style.height = `${paneHeight}px`;
      horizontal.style.top = `${boundedY}px`;
      horizontal.style.width = `${paneWidth}px`;
      marker.style.left = `${boundedX}px`;
      marker.style.top = `${boundedY}px`;
      marker.style.opacity = snapped ? "1" : "0";
      label.style.left = `${paneWidth + axisWidth - labelWidth}px`;
      label.style.top = `${Math.max(0, Math.min(paneHeight - 20, boundedY - 10))}px`;
      label.style.width = `${labelWidth}px`;
      const displayedPrice = snapped
        ? price
        : barsByTime.size > 0
          ? (chartType === "candles" ? candleSeries : lineSeries)
              .coordinateToPrice(boundedY) ?? price
          : price;
      label.textContent = displayedPrice === null ? "—" : formatPrice(displayedPrice);
      label.classList.toggle("!border-emerald-500/40", snapped);
      label.classList.toggle("!bg-[#064e3b]", snapped);
    };

    const animateCrosshair = (timestamp: number) => {
      animationFrame = 0;
      if (!target) return;
      const elapsed = lastFrameTime === 0 ? 16 : Math.min(timestamp - lastFrameTime, 32);
      lastFrameTime = timestamp;
      if (!displayed) displayed = { x: target.x, y: target.y };
      const factor = Math.min(1, elapsed / 100);
      displayed.x += (target.x - displayed.x) * factor;
      displayed.y += (target.y - displayed.y) * factor;
      updateOverlay(displayed.x, displayed.y, target.price, target.snapped);
      if (
        Math.abs(target.x - displayed.x) > 0.1 ||
        Math.abs(target.y - displayed.y) > 0.1
      ) {
        animationFrame = requestAnimationFrame(animateCrosshair);
      } else {
        displayed = { x: target.x, y: target.y };
      }
    };

    const scheduleCrosshair = () => {
      if (!animationFrame) {
        lastFrameTime = 0;
        animationFrame = requestAnimationFrame(animateCrosshair);
      }
    };

    const crosshairHandler = (param: MouseEventParams<Time>) => {
      if (!param.point) {
        lastCrosshairParam = null;
        hideCrosshair();
        setHoverBar(null);
        if (animationFrame) cancelAnimationFrame(animationFrame);
        animationFrame = 0;
        return;
      }
      lastCrosshairParam = param;
      pointer = { x: param.point.x, y: param.point.y };
      const eventTime = toTimestamp(param.time ?? chart.timeScale().coordinateToTime(pointer.x));
      let nextBar = eventTime === null ? null : barsByTime.get(eventTime) ?? null;
      if (!nextBar) {
        let nearestDistance = Infinity;
        for (const bar of orderedBars) {
          const x = chart.timeScale().timeToCoordinate(bar.time);
          if (x === null) continue;
          const distance = Math.abs(x - pointer.x);
          if (distance < nearestDistance) {
            nearestDistance = distance;
            nextBar = bar;
          }
        }
      }
      setHoverBar((current) => current === nextBar ? current : nextBar);
      const freePrice = barsByTime.size > 0
        ? (chartType === "candles" ? candleSeries : lineSeries)
            .coordinateToPrice(pointer.y) ?? lastPrice
        : lastPrice;
      const barX = nextBar ? chart.timeScale().timeToCoordinate(nextBar.time) : null;
      const candidates = nextBar && barX !== null && chartType === "candles"
        ? [
            { level: "high", price: nextBar.high },
            { level: "low", price: nextBar.low },
            { level: "bodyHigh", price: Math.max(nextBar.open, nextBar.close) },
            { level: "bodyLow", price: Math.min(nextBar.open, nextBar.close) },
          ]
        : nextBar && barX !== null
          ? [{ level: "close", price: nextBar.close }]
          : [];
      const nearest = candidates
        .map((candidate) => ({
          ...candidate,
          y: (chartType === "candles" ? candleSeries : lineSeries)
            .priceToCoordinate(candidate.price),
        }))
        .filter((candidate): candidate is typeof candidate & { y: number } =>
          candidate.y !== null
        )
        .map((candidate) => ({
          ...candidate,
          distance: Math.abs(candidate.y - pointer!.y),
        }))
        .sort((a, b) => a.distance - b.distance)[0];
      const retained = previousSnap && nextBar &&
        previousSnap.time === toTimestamp(nextBar.time)
        ? candidates.find((candidate) =>
            candidate.level === previousSnap?.level &&
            Math.abs(
              ((chartType === "candles" ? candleSeries : lineSeries)
                .priceToCoordinate(candidate.price) ?? Infinity) - pointer!.y
            ) <= 14
          )
        : undefined;
      const snapCandidate = retained
        ? {
            ...retained,
            y: (chartType === "candles" ? candleSeries : lineSeries)
              .priceToCoordinate(retained.price),
          }
        : nearest && nearest.distance <= 9
          ? nearest
          : null;

      if (snapCandidate && barX !== null && snapCandidate.y !== null) {
        previousSnap = {
          time: toTimestamp(nextBar!.time)!,
          price: snapCandidate.price,
          level: snapCandidate.level,
        };
        target = {
          x: barX,
          y: snapCandidate.y,
          price: snapCandidate.price,
          snapped: true,
        };
      } else {
        previousSnap = null;
        target = { x: pointer.x, y: pointer.y, price: freePrice, snapped: false };
      }
      scheduleCrosshair();
    };
    chart.subscribeCrosshairMove(crosshairHandler);

    let mounted = true;
    const isCurrentSubscription = () =>
      mounted && subscriptionIdRef.current === subscriptionId;
    const intervalSeconds = TIMEFRAME_SECONDS[timeframe];
    const to = Math.floor(Date.now() / 1000) as UTCTimestamp;
    const refreshMarketSummary = () => {
      Promise.all([provider.getLastPrice(), provider.get24hChange()])
        .then(([price, change]) => {
          if (!mounted) return;
          setLastPrice(price);
          setChange24h(change);
        })
        .catch((error: unknown) => {
          if (mounted) {
            console.error(`Unable to update ${TOKEN_CONFIG.ticker} market summary.`, error);
          }
        });
    };

    const applyRealtimeBar = (bar: VtgxBar) => {
      if (!isCurrentSubscription() || !seriesReady) return;
      const timestamp = toTimestamp(bar.time);
      if (timestamp === null) {
        logRejectedBar(bar.time, timeframe, "invalid realtime timestamp");
        return;
      }
      const alignedTime = alignUtcTime(timestamp, timeframe);
      const alignedBar = { ...bar, time: alignedTime as UTCTimestamp };
      if (lastCandleTime !== null && alignedTime < lastCandleTime) {
        logRejectedBar(alignedTime, timeframe, "older than the latest candle");
        return;
      }
      if (lastLineTime !== null && alignedTime < lastLineTime) {
        logRejectedBar(alignedTime, timeframe, "older than the latest line point");
        return;
      }
      if (lastVolumeTime !== null && alignedTime < lastVolumeTime) {
        logRejectedBar(alignedTime, timeframe, "older than the latest volume bar");
        return;
      }

      const candleData = alignedBar;
      const lineData = { time: alignedBar.time, value: alignedBar.close };
      const volumeData = {
        time: alignedBar.time,
        value: alignedBar.volume ?? 0,
        color: alignedBar.close >= alignedBar.open
          ? "rgba(16, 185, 129, 0.34)"
          : "rgba(248, 113, 113, 0.32)",
      };

      if (lastCandleTime === null) {
        candleSeries.setData([candleData]);
        lineSeries.setData([lineData]);
        volumeSeries.setData([volumeData]);
      } else {
        candleSeries.update(candleData);
        lineSeries.update(lineData);
        volumeSeries.update(volumeData);
      }
      lastCandleTime = alignedTime;
      lastLineTime = alignedTime;
      lastVolumeTime = alignedTime;
      barsByTime.set(alignedTime, alignedBar);
      const existingIndex = orderedBars.findIndex(
        (existing) => toTimestamp(existing.time) === alignedTime
      );
      if (existingIndex === -1) {
        orderedBars.push(alignedBar);
      } else {
        orderedBars[existingIndex] = alignedBar;
      }
      setLastPrice(alignedBar.close);
      provider.get24hChange().then((value) => {
        if (isCurrentSubscription()) setChange24h(value);
      }).catch((error: unknown) => {
        if (isCurrentSubscription()) {
          console.error(`Unable to update ${TOKEN_CONFIG.ticker} 24-hour change.`, error);
        }
      });
      setHasBars(true);
    };

    let unsubscribe = () => {};
    try {
      unsubscribe = provider.subscribeBars(timeframe, (incomingBar) => {
        if (!isCurrentSubscription()) return;
        const timestamp = toTimestamp(incomingBar.time);
        if (timestamp === null) {
          logRejectedBar(incomingBar.time, timeframe, "invalid realtime timestamp");
          return;
        }
        const alignedTime = alignUtcTime(timestamp, timeframe);
        const normalizedBar = {
          ...incomingBar,
          time: alignedTime as UTCTimestamp,
        };
        if (!seriesReady) {
          pendingBars.set(alignedTime, normalizedBar);
          return;
        }
        applyRealtimeBar(normalizedBar);
      });
      subscriptionCleanupRef.current = unsubscribe;
    } catch (error: unknown) {
      setFeedError(
        error instanceof Error ? error.message : "Unable to subscribe to token chart data."
      );
    }

    provider
      .getBars(
        timeframe,
        (Number(to) - intervalSeconds * 300) as UTCTimestamp,
        to
      )
      .then((bars) => {
        if (!isCurrentSubscription()) return;
        const normalizedBars = bars.flatMap((bar) => {
          const timestamp = toTimestamp(bar.time);
          if (timestamp === null) {
            logRejectedBar(bar.time, timeframe, "invalid historical timestamp");
            return [];
          }
          const alignedTime = alignUtcTime(timestamp, timeframe);
          return [{ ...bar, time: alignedTime as UTCTimestamp }];
        });
        orderedBars = Array.from(
          new Map(
            normalizedBars.map((bar) => [toTimestamp(bar.time)!, bar])
          ).values()
        ).sort((a, b) => toTimestamp(a.time)! - toTimestamp(b.time)!);
        orderedBars.forEach((bar) => barsByTime.set(toTimestamp(bar.time)!, bar));
        candleSeries.setData(orderedBars);
        lineSeries.setData(
          orderedBars.map((bar) => ({ time: bar.time, value: bar.close }))
        );
        volumeSeries.setData(
          orderedBars.map((bar) => ({
            time: bar.time,
            value: bar.volume ?? 0,
            color: bar.close >= bar.open ? "rgba(16, 185, 129, 0.34)" : "rgba(248, 113, 113, 0.32)",
          }))
        );
        lastCandleTime = orderedBars.length
          ? toTimestamp(orderedBars[orderedBars.length - 1].time)
          : null;
        lastLineTime = lastCandleTime;
        lastVolumeTime = lastCandleTime;
        seriesReady = true;
        if (orderedBars.length > 0) {
          chart.timeScale().fitContent();
          setHasBars(true);
        }
        refreshMarketSummary();
        Array.from(pendingBars.values())
          .sort((a, b) => toTimestamp(a.time)! - toTimestamp(b.time)!)
          .forEach(applyRealtimeBar);
        pendingBars.clear();
      })
      .catch((error: unknown) => {
        if (isCurrentSubscription()) {
          unsubscribe();
          if (subscriptionCleanupRef.current === unsubscribe) {
            subscriptionCleanupRef.current = () => {};
          }
          setFeedError(error instanceof Error ? error.message : "Unable to load token chart data.");
        }
      });

    const resizeObserver = new ResizeObserver(([entry]) => {
      if (entry && chartRef.current === chart) {
        chart.applyOptions({ width: Math.max(320, Math.floor(entry.contentRect.width)) });
        if (lastCrosshairParam) {
          crosshairHandler(lastCrosshairParam);
        }
      }
    });
    resizeObserver.observe(host);

    return () => {
      mounted = false;
      unsubscribe();
      if (subscriptionCleanupRef.current === unsubscribe) {
        subscriptionCleanupRef.current = () => {};
      }
      chart.unsubscribeCrosshairMove(crosshairHandler);
      resizeObserver.disconnect();
      if (animationFrame) cancelAnimationFrame(animationFrame);
      chart.remove();
      if (chartRef.current === chart) chartRef.current = null;
    };
  }, [provider, timeframe, logarithmic, chartType, showVolume]);

  return (
    <div className="relative overflow-hidden rounded-md border border-slate-800 bg-[#111723]">
      <div className="border-b border-slate-800 px-3 py-2">
        <div className="flex min-w-0 flex-col items-start gap-1">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="font-mono text-lg font-semibold text-slate-100 md:text-xl">{TOKEN_CONFIG.pair}</span>
            <span className="font-mono text-lg font-semibold text-slate-400 md:text-xl">{timeframe}</span>
          </div>
          <div className="flex min-h-4 flex-wrap items-baseline gap-x-2 gap-y-0.5 font-mono text-[9px] tabular-nums">
            <span className="font-semibold text-slate-100">
              {lastPrice !== null ? formatPrice(lastPrice) : "Pre-launch"}
            </span>
            {change24h !== null ? (
              <span className={`font-medium ${change24h.value >= 0 ? "text-emerald-300" : "text-rose-400"}`}>
                24H {formatSignedPrice(change24h.value)} ({change24h.percent >= 0 ? "+" : ""}{change24h.percent.toFixed(2)}%)
              </span>
            ) : (
              <span className="text-slate-500">24H —</span>
            )}
          </div>
        </div>
        <div className="flex min-h-10 flex-wrap items-center gap-x-4 gap-y-1 pt-1 font-mono text-[9px] tabular-nums">
          {hoverBar ? (
            <>
              <span className="text-slate-500">{formatBarTime(hoverBar.time, timeframe)}</span>
              <span className="text-slate-400">O <b className="text-slate-200">{formatPrice(hoverBar.open)}</b></span>
              <span className="text-slate-400">H <b className="text-emerald-300">{formatPrice(hoverBar.high)}</b></span>
              <span className="text-slate-400">L <b className="text-slate-200">{formatPrice(hoverBar.low)}</b></span>
              <span className="text-slate-400">C <b className={candleChange >= 0 ? "text-emerald-300" : "text-rose-400"}>{formatPrice(hoverBar.close)}</b></span>
              {showVolume && (
                <span className="text-slate-400">VOL <b className="text-slate-200">{formatVolume(hoverBar.volume)}</b></span>
              )}
              <span className={candleChange >= 0 ? "text-emerald-300" : "text-rose-400"}>
                {formatSignedPrice(candleChange)} ({candleChangePercent === null ? "—" : `${candleChangePercent >= 0 ? "+" : ""}${candleChangePercent.toFixed(2)}%`})
              </span>
            </>
          ) : (
            <span className="text-slate-500">Move the crosshair over a bar for OHLCV data</span>
          )}
        </div>
      </div>
      <div ref={hostRef} className="relative h-[350px] w-full">
        <div ref={overlayRef} className="pointer-events-none absolute inset-0 z-10 opacity-0">
          <div ref={verticalCrosshairRef} className="absolute top-0 w-px bg-slate-400/40" />
          <div ref={horizontalCrosshairRef} className="absolute left-0 h-px bg-slate-400/40" />
          <div
            ref={snapMarkerRef}
            className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-emerald-300 bg-[#111723] opacity-0 shadow-[0_0_8px_rgba(16,185,129,0.65)]"
          />
          <div
            ref={priceLabelRef}
            className="absolute flex h-5 items-center justify-center overflow-hidden border border-slate-700 bg-[#1E293B] px-1 text-[9px] font-mono tabular-nums text-slate-100"
          />
        </div>
      </div>
      {!hasBars && !feedError && (
        <div className="pointer-events-none absolute inset-x-0 bottom-10 top-10 flex items-center justify-center bg-[#111723]/75 px-5 text-center backdrop-blur-[1px]">
          <div>
            <p className="text-sm font-medium text-slate-200">
              {simulated ? "Loading simulated preview…" : "No listed market data"}
            </p>
            <p className="mt-1 text-[11px] text-slate-500">
              {simulated
                ? `Illustrative data only — not a ${TOKEN_CONFIG.ticker} market price.`
                : `The candlestick chart will populate once an authorized ${TOKEN_CONFIG.ticker} datafeed is connected.`}
            </p>
          </div>
        </div>
      )}
      {feedError && (
        <div className="absolute inset-x-4 bottom-4 rounded border border-rose-500/20 bg-[#111723] px-3 py-2 text-xs text-rose-300" role="alert">
          {feedError}
        </div>
      )}
    </div>
  );
}

function formatPrice(value: number) {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 4,
    maximumFractionDigits: 6,
  });
}

function toTimestamp(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.floor(value > 1e12 ? value / 1000 : value);
  }
  if (typeof value === "string") {
    const numeric = Number(value);
    if (value.trim() !== "" && Number.isFinite(numeric)) {
      return Math.floor(numeric > 1e12 ? numeric / 1000 : numeric);
    }
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? Math.floor(parsed / 1000) : null;
  }
  if (typeof value === "object" && value !== null) {
    const businessDay = value as { year?: unknown; month?: unknown; day?: unknown };
    if (
      Number.isInteger(businessDay.year) &&
      Number.isInteger(businessDay.month) &&
      Number.isInteger(businessDay.day)
    ) {
      return Math.floor(
        Date.UTC(
          Number(businessDay.year),
          Number(businessDay.month) - 1,
          Number(businessDay.day)
        ) / 1000
      );
    }
  }
  return null;
}

function logRejectedBar(time: unknown, timeframe: VtgxTimeframe, reason: string) {
  if (process.env.NODE_ENV === "development") {
    console.warn(
      `[${TOKEN_CONFIG.ticker}] Ignoring ${timeframe} bar (${String(time)}): ${reason}.`
    );
  }
}

function formatVolume(value: number | undefined) {
  return value === undefined
    ? "—"
    : value.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatSignedPrice(value: number) {
  return `${value >= 0 ? "+" : "−"}${formatPrice(Math.abs(value))}`;
}

function formatBarTime(time: UTCTimestamp, timeframe: VtgxTimeframe) {
  const timestamp = toTimestamp(time);
  if (timestamp === null) return "—";
  const date = new Date(timestamp * 1000);
  return timeframe === "1D"
    ? date.toLocaleDateString("en-US")
    : date.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
