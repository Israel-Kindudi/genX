export type BenchmarkSymbol = "VTGX" | "BTCUSD" | "XAUUSD" | "SP500";

export type BenchmarkPoint = {
  time: number;
  value: number;
};

export interface BenchmarkDatafeed {
  getBars(
    symbol: BenchmarkSymbol,
    from: number,
    to: number
  ): Promise<BenchmarkPoint[]>;
  subscribeBars(
    symbol: BenchmarkSymbol,
    onBar: (point: BenchmarkPoint) => void
  ): () => void;
}

export const unavailableBenchmarkDatafeed: BenchmarkDatafeed = {
  async getBars() {
    return [];
  },
  subscribeBars() {
    return () => {};
  },
};

export function createDevelopmentBenchmarkMock(
  environment: string
): BenchmarkDatafeed {
  if (environment !== "development") {
    throw new Error("Mock benchmark data is available in development only.");
  }

  const anchor: Record<BenchmarkSymbol, number> = {
    VTGX: 1,
    BTCUSD: 65000,
    XAUUSD: 2300,
    SP500: 5200,
  };
  const stepMs = 86400000;

  return {
    async getBars(symbol, from, to) {
      const points: BenchmarkPoint[] = [];
      const firstDay = Math.floor(from / stepMs);
      const lastDay = Math.floor(to / stepMs);
      for (let day = firstDay; day <= lastDay; day += 1) {
        const wave = Math.sin(day / 17 + symbol.length) * 0.025;
        const trend = (day - firstDay) * 0.00012;
        points.push({
          time: day * stepMs,
          value: anchor[symbol] * (1 + wave + trend),
        });
      }
      return points;
    },
    subscribeBars(_symbol, _onBar) {
      return () => {};
    },
  };
}
