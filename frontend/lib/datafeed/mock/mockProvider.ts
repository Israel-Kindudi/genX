import type { UTCTimestamp } from "lightweight-charts";
import type { MinuteMarketSource, VtgxBar } from "@/lib/vtgxDatafeed";

const MINUTE_SECONDS = 60;
const HISTORY_START = Math.floor(Date.UTC(2025, 11, 29) / 1000);
const SEED = 0x51a7c0de;

type MinuteArrays = {
  open: Float64Array;
  high: Float64Array;
  low: Float64Array;
  close: Float64Array;
  volume: Float64Array;
};

let minuteHistory = createMinuteArrays(65536);
let generatedMinutes = -1;
let randomState = SEED;
let price = 5;
let logPrice = Math.log(price);
let regime: "uptrend" | "downtrend" | "range" = "range";
let regimeMinutesLeft = 0;
let targetDrift = 0;
let drift = 0;
let targetVolatility = 0.00042;
let volatility = targetVolatility;
let volatilityClusterMinutesLeft = 0;
let impulseRetraceLeft = 0;
let impulseRetraceStep = 0;
const liveListeners = new Set<(bar: VtgxBar) => void>();
let liveTimer: ReturnType<typeof setInterval> | null = null;
let liveMinute = -1;
let livePrice = 5;
let liveVolatility = 0.00042;
let liveBar: VtgxBar | null = null;

function createMinuteArrays(capacity: number): MinuteArrays {
  return {
    open: new Float64Array(capacity),
    high: new Float64Array(capacity),
    low: new Float64Array(capacity),
    close: new Float64Array(capacity),
    volume: new Float64Array(capacity),
  };
}

function ensureCapacity(required: number) {
  if (required <= minuteHistory.open.length) return;
  const next = createMinuteArrays(Math.max(required, minuteHistory.open.length * 2));
  for (const key of ["open", "high", "low", "close", "volume"] as const) {
    next[key].set(minuteHistory[key].subarray(0, generatedMinutes + 1));
  }
  minuteHistory = next;
}

function random() {
  randomState ^= randomState << 13;
  randomState ^= randomState >>> 17;
  randomState ^= randomState << 5;
  return (randomState >>> 0) / 4294967296;
}

function randomBetween(min: number, max: number) {
  return min + random() * (max - min);
}

function randomNormal() {
  let total = 0;
  for (let sample = 0; sample < 12; sample += 1) total += random();
  return total - 6;
}

function startRegime() {
  const choices = ["uptrend", "downtrend", "range"] as const;
  let next = choices[Math.floor(random() * choices.length)];
  if (next === regime && random() < 0.65) {
    next = choices[(choices.indexOf(next) + 1 + Math.floor(random() * 2)) % choices.length];
  }
  regime = next;
  regimeMinutesLeft = Math.floor(randomBetween(2 * 1440, 18 * 1440));
  targetDrift =
    regime === "uptrend"
      ? randomBetween(0.0000045, 0.000008)
      : regime === "downtrend"
        ? -randomBetween(0.0000045, 0.000008)
        : randomBetween(-0.0000005, 0.0000005);
}

function updateVolatilityCluster() {
  if (volatilityClusterMinutesLeft > 0) {
    volatilityClusterMinutesLeft -= 1;
    return;
  }
  targetVolatility = randomBetween(0.00025, 0.00085);
  volatilityClusterMinutesLeft = Math.floor(randomBetween(8 * 60, 4 * 1440));
}

function historicalMinuteBar(index: number): VtgxBar {
  return {
    time: (HISTORY_START + index * MINUTE_SECONDS) as UTCTimestamp,
    open: minuteHistory.open[index],
    high: minuteHistory.high[index],
    low: minuteHistory.low[index],
    close: minuteHistory.close[index],
    volume: minuteHistory.volume[index],
    isComplete: true,
  };
}

function generateHistoricalMinute(index: number) {
  ensureCapacity(index + 1);
  if (index === 0) {
    const open = 5;
    const close = open * Math.exp(randomNormal() * volatility);
    minuteHistory.open[index] = open;
    minuteHistory.close[index] = close;
    minuteHistory.high[index] = Math.max(open, close);
    minuteHistory.low[index] = Math.min(open, close);
    minuteHistory.volume[index] = randomBetween(120, 520);
    price = close;
    logPrice = Math.log(close);
    generatedMinutes = index;
    return;
  }

  if (regimeMinutesLeft <= 0) startRegime();
  regimeMinutesLeft -= 1;
  updateVolatilityCluster();
  drift += (targetDrift - drift) * 0.004;
  volatility += (targetVolatility - volatility) * 0.003;

  let impulse = 0;
  if (impulseRetraceLeft > 0) {
    impulse = impulseRetraceStep;
    impulseRetraceLeft -= 1;
  } else if (random() < 1 / 12000) {
    const direction =
      regime === "uptrend"
        ? 1
        : regime === "downtrend"
          ? -1
          : random() < 0.5
            ? -1
            : 1;
    const size = direction * randomBetween(0.018, 0.045);
    impulse = size;
    impulseRetraceLeft = Math.floor(randomBetween(20, 100));
    impulseRetraceStep = -(size * randomBetween(0.42, 0.66)) / impulseRetraceLeft;
  }

  const open = price;
  const meanReversion = (Math.log(5) - logPrice) * 0.00001;
  const change = drift + meanReversion + randomNormal() * volatility + impulse;
  logPrice += change;
  price = Math.max(0.05, Math.exp(logPrice));
  const close = price;
  const body = Math.abs(close - open);
  const wickBase = open * volatility * randomBetween(0.08, 0.35);
  let upperWick = body * randomBetween(0.12, 0.65) + wickBase;
  let lowerWick = body * randomBetween(0.12, 0.65) + wickBase;
  const largeWick = random() < 0.00018;
  if (largeWick) {
    const wick = open * randomBetween(0.012, 0.05);
    if (random() < 0.5) upperWick += wick;
    else lowerWick += wick;
  }

  const amplitude = Math.abs(change) / Math.max(volatility, 0.0001);
  const regimeVolume = regime === "range" ? 0.72 : 1;
  const breakoutVolume = impulse !== 0 || largeWick ? randomBetween(2.2, 5.5) : 1;
  const volume =
    randomBetween(180, 850) *
    regimeVolume *
    (0.35 + amplitude * 0.8) *
    breakoutVolume *
    Math.max(0.2, 1 + randomNormal() * 0.28);

  minuteHistory.open[index] = open;
  minuteHistory.high[index] = Math.max(open, close) + upperWick;
  minuteHistory.low[index] = Math.max(0.01, Math.min(open, close) - lowerWick);
  minuteHistory.close[index] = close;
  minuteHistory.volume[index] = Math.max(1, volume);
  generatedMinutes = index;
}

function ensureHistoricalMinutes(endIndex: number) {
  while (generatedMinutes < endIndex) generateHistoricalMinute(generatedMinutes + 1);
}

function getHistory(from: number, to: number) {
  const startIndex = Math.max(
    0,
    Math.ceil((from - HISTORY_START) / MINUTE_SECONDS)
  );
  const endIndex = Math.min(
    generatedMinutes,
    Math.floor((to - HISTORY_START) / MINUTE_SECONDS)
  );
  const bars: VtgxBar[] = [];
  for (let index = startIndex; index <= endIndex; index += 1) {
    bars.push(historicalMinuteBar(index));
  }
  return bars;
}

function writeLiveBar(bar: VtgxBar) {
  const index = Math.floor((Number(bar.time) - HISTORY_START) / MINUTE_SECONDS);
  if (index < 0) return;
  ensureCapacity(index + 1);
  minuteHistory.open[index] = bar.open;
  minuteHistory.high[index] = bar.high;
  minuteHistory.low[index] = bar.low;
  minuteHistory.close[index] = bar.close;
  minuteHistory.volume[index] = bar.volume ?? 0;
  generatedMinutes = Math.max(generatedMinutes, index);
}

function startLiveStream() {
  if (liveTimer) return;

  liveTimer = setInterval(() => {
    const minute = Math.floor(Date.now() / (MINUTE_SECONDS * 1000));
    const index = Math.max(
      0,
      Math.floor((minute * MINUTE_SECONDS - HISTORY_START) / MINUTE_SECONDS)
    );

    if (liveMinute !== minute) {
      if (liveBar) {
        liveBar = { ...liveBar, isComplete: true };
        writeLiveBar(liveBar);
        liveListeners.forEach((listener) => listener({ ...liveBar! }));
        price = livePrice;
        logPrice = Math.log(livePrice);
      }

      ensureHistoricalMinutes(index);
      liveMinute = minute;
      livePrice = index > 0 ? historicalMinuteBar(index - 1).close : 5;
      liveVolatility = randomBetween(0.00025, 0.00085);
      liveBar = {
        time: (minute * MINUTE_SECONDS) as UTCTimestamp,
        open: livePrice,
        high: livePrice,
        low: livePrice,
        close: livePrice,
        volume: 0,
        isComplete: false,
      };
    }

    const close = Math.max(
      0.05,
      livePrice * Math.exp(randomNormal() * liveVolatility * Math.sqrt(5 / 60))
    );
    livePrice = close;
    liveBar = {
      ...liveBar!,
      close,
      high: Math.max(liveBar!.high, close),
      low: Math.min(liveBar!.low, close),
      volume: (liveBar!.volume ?? 0) + randomBetween(15, 110),
      isComplete: false,
    };
    price = close;
    logPrice = Math.log(close);
    writeLiveBar(liveBar);
    liveListeners.forEach((listener) => listener({ ...liveBar! }));
  }, 5000);
}

export function createMockProvider(): MinuteMarketSource {
  if (process.env.NODE_ENV !== "development") {
    throw new Error("Mock market data is available in development only.");
  }

  return {
    async getBars(from, to) {
      const nowMinute = Math.floor(Date.now() / (MINUTE_SECONDS * 1000));
      const endIndex = Math.max(
        0,
        Math.floor((nowMinute * MINUTE_SECONDS - HISTORY_START) / MINUTE_SECONDS)
      );
      ensureHistoricalMinutes(endIndex);
      const bars = getHistory(Number(from), Number(to));
      const currentTimestamp = HISTORY_START + endIndex * MINUTE_SECONDS;
      const current = bars.find((bar) => Number(bar.time) === currentTimestamp);
      if (current) current.isComplete = false;
      return bars;
    },
    subscribeBars(callback) {
      liveListeners.add(callback);
      startLiveStream();
      return () => {
        liveListeners.delete(callback);
        if (liveListeners.size === 0 && liveTimer) {
          clearInterval(liveTimer);
          liveTimer = null;
        }
      };
    },
  };
}
