import type { UTCTimestamp } from "lightweight-charts";

export type VtgxTimeframe = "1m" | "5m" | "15m" | "1H" | "4H" | "1D";

export type VtgxBar = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  isComplete?: boolean;
};

export type MarketChange = {
  value: number;
  percent: number;
};

export interface MarketDataProvider {
  getBars(
    timeframe: VtgxTimeframe,
    from: UTCTimestamp,
    to: UTCTimestamp
  ): Promise<VtgxBar[]>;
  subscribeBars(
    timeframe: VtgxTimeframe,
    callback: (bar: VtgxBar) => void
  ): () => void;
  getLastPrice(): Promise<number | null>;
  get24hChange(): Promise<MarketChange | null>;
}

export interface MinuteMarketSource {
  getBars(from: UTCTimestamp, to: UTCTimestamp): Promise<VtgxBar[]>;
  subscribeBars(callback: (bar: VtgxBar) => void): () => void;
}

export interface TimeframeMarketSource {
  getBars(
    timeframe: VtgxTimeframe,
    from: UTCTimestamp,
    to: UTCTimestamp
  ): Promise<VtgxBar[]>;
  subscribeBars(
    timeframe: VtgxTimeframe,
    callback: (bar: VtgxBar) => void
  ): () => void;
}

export type MarketSource =
  | { mode: "minute-only"; source: MinuteMarketSource }
  | { mode: "timeframe-bars"; source: TimeframeMarketSource };

export const TIMEFRAME_SECONDS: Record<VtgxTimeframe, number> = {
  "1m": 60,
  "5m": 5 * 60,
  "15m": 15 * 60,
  "1H": 60 * 60,
  "4H": 4 * 60 * 60,
  "1D": 24 * 60 * 60,
};

export function alignUtcTime(time: number, timeframe: VtgxTimeframe) {
  const interval = TIMEFRAME_SECONDS[timeframe];
  return Math.floor(time / interval) * interval;
}

export function aggregateVtgxBars(
  minuteBars: VtgxBar[],
  timeframe: VtgxTimeframe,
  nowSeconds = Math.floor(Date.now() / 1000)
): VtgxBar[] {
  const buckets = new Map<number, VtgxBar>();
  const orderedBars = normalizeMinuteBars(minuteBars);

  for (const bar of orderedBars) {
    const time = alignUtcTime(Number(bar.time), timeframe);
    const existing = buckets.get(time);
    if (!existing) {
      buckets.set(time, {
        ...bar,
        time: time as UTCTimestamp,
        isComplete: time + TIMEFRAME_SECONDS[timeframe] <= nowSeconds,
      });
    } else {
      existing.high = Math.max(existing.high, bar.high);
      existing.low = Math.min(existing.low, bar.low);
      existing.close = bar.close;
      existing.isComplete = time + TIMEFRAME_SECONDS[timeframe] <= nowSeconds;
      if (existing.volume !== undefined && bar.volume !== undefined) {
        existing.volume += bar.volume;
      } else {
        existing.volume = undefined;
      }
    }
  }

  return Array.from(buckets.values());
}

export function normalizeMinuteBars(bars: VtgxBar[]) {
  const sorted = [...bars].sort((a, b) => Number(a.time) - Number(b.time));
  const barsByTime = new Map<number, VtgxBar>();
  for (const bar of sorted) barsByTime.set(Number(bar.time), bar);
  const ordered = Array.from(barsByTime.values());
  let previous: VtgxBar | undefined;

  return ordered.map((sourceBar) => {
    let bar = sourceBar;
    if (previous && Number(sourceBar.time) > Number(previous.time)) {
      const open = previous.close;
      bar = {
        ...sourceBar,
        open,
        high: Math.max(sourceBar.high, open),
        low: Math.min(sourceBar.low, open),
      };
    }
    previous = bar;
    return bar;
  });
}

export function createMarketDataProvider(
  marketSource: MarketSource
): MarketDataProvider {
  const recentMinuteBars = new Map<number, VtgxBar>();
  const recentBarsByTimeframe = new Map<VtgxTimeframe, Map<number, VtgxBar>>();

  function remember(timeframe: VtgxTimeframe, bars: VtgxBar[]) {
    let cache = recentBarsByTimeframe.get(timeframe);
    if (!cache) {
      cache = new Map();
      recentBarsByTimeframe.set(timeframe, cache);
    }
    for (const bar of bars) cache.set(Number(bar.time), bar);
  }

  function orderedCache(timeframe: VtgxTimeframe) {
    return Array.from(recentBarsByTimeframe.get(timeframe)?.values() ?? [])
      .sort((a, b) => Number(a.time) - Number(b.time));
  }

  function getCurrentPriceBars() {
    return orderedCache("1m");
  }

  function getBars(
    timeframe: VtgxTimeframe,
    from: UTCTimestamp,
    to: UTCTimestamp
  ) {
    if (marketSource.mode === "timeframe-bars") {
      return marketSource.source.getBars(timeframe, from, to).then((bars) => {
        const normalized = normalizeTimeframeBars(bars, timeframe);
        remember(timeframe, normalized);
        return normalized;
      });
    }

    return marketSource.source.getBars(from, to).then((bars) => {
      for (const bar of normalizeMinuteBars(bars)) {
        recentMinuteBars.set(Number(bar.time), bar);
      }
      const allMinutes = Array.from(recentMinuteBars.values()).sort(
        (a, b) => Number(a.time) - Number(b.time)
      );
      const aggregated = aggregateVtgxBars(allMinutes, timeframe);
      remember("1m", allMinutes);
      remember(timeframe, aggregated);
      return aggregated.filter(
        (bar) => Number(bar.time) <= Number(to) &&
          Number(bar.time) + TIMEFRAME_SECONDS[timeframe] > Number(from)
      );
    });
  }

  function subscribeBars(
    timeframe: VtgxTimeframe,
    callback: (bar: VtgxBar) => void
  ) {
    if (marketSource.mode === "timeframe-bars") {
      return marketSource.source.subscribeBars(timeframe, (bar) => {
        const [normalized] = normalizeTimeframeBars([bar], timeframe);
        if (!normalized) return;
        remember(timeframe, [normalized]);
        callback(normalized);
      });
    }

    return marketSource.source.subscribeBars((sourceBar) => {
      const previousBar = Array.from(recentMinuteBars.values())
        .filter((item) => Number(item.time) < Number(sourceBar.time))
        .sort((a, b) => Number(b.time) - Number(a.time))[0];
      const [bar] = normalizeMinuteBars(
        previousBar ? [previousBar, sourceBar] : [sourceBar]
      ).slice(-1);
      recentMinuteBars.set(Number(bar.time), bar);
      remember("1m", [bar]);
      const currentMinutes = Array.from(recentMinuteBars.values())
        .filter(
          (item) =>
            alignUtcTime(Number(item.time), timeframe) ===
            alignUtcTime(Number(bar.time), timeframe)
        )
        .sort((a, b) => Number(a.time) - Number(b.time));
      const [aggregated] = aggregateVtgxBars(currentMinutes, timeframe);
      if (!aggregated) return;
      remember(timeframe, [aggregated]);
      callback(aggregated);
    });
  }

  return {
    getBars,
    subscribeBars,
    async getLastPrice() {
      const end = Math.floor(Date.now() / 1000) as UTCTimestamp;
      const start = (Number(end) - 24 * 60 * 60) as UTCTimestamp;
      await getBars("1m", start, end);
      return getCurrentPriceBars().at(-1)?.close ?? null;
    },
    async get24hChange() {
      const end = Math.floor(Date.now() / 1000) as UTCTimestamp;
      const start = (Number(end) - 25 * 60 * 60) as UTCTimestamp;
      const bars = await getBars("1H", start, end);
      const ordered = [...bars].sort((a, b) => Number(a.time) - Number(b.time));
      const last = ordered.at(-1);
      if (!last) return null;
      const targetTime = Number(last.time) - 24 * 60 * 60;
      const reference = [...ordered]
        .reverse()
        .find((bar) => Number(bar.time) <= targetTime);
      if (!reference || reference.close === 0) return null;
      const value = last.close - reference.close;
      return { value, percent: (value / reference.close) * 100 };
    },
  };
}

function normalizeTimeframeBars(
  bars: VtgxBar[],
  timeframe: VtgxTimeframe
): VtgxBar[] {
  const ordered = [...bars].sort((a, b) => Number(a.time) - Number(b.time));
  const interval = TIMEFRAME_SECONDS[timeframe];
  return ordered.map((bar) => {
    const time = alignUtcTime(Number(bar.time), timeframe);
    return {
      ...bar,
      time: time as UTCTimestamp,
      isComplete: bar.isComplete ?? time + interval <= Date.now() / 1000,
    };
  });
}
