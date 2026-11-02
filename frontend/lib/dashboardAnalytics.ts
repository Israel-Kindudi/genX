import type { CapitalFlow, LiveEquity, LiveTrade } from "@/lib/useLiveTrades";

export type FlowAdjustedEquity = LiveEquity & {
  timeWeightedEquity: number;
  timeWeightedBalance: number;
  timeWeightedReturn: number;
  underwater: number;
};

export type DashboardMetrics = {
  realizedPnL: number;
  winRate: number;
  maxDrawdown: number;
  profitFactor: number | null;
  tradeSharpe: number | null;
  calmar: number | null;
  averageRiskReward: number | null;
  expectancy: number;
  closedTrades: number;
  openTrades: number;
  dailyObservations: number;
};

export type MonthlyReturn = {
  year: number;
  month: number;
  value: number;
};

export function calculateMaxDrawdown(points: LiveEquity[]) {
  let peak = Number.NEGATIVE_INFINITY;
  let maxDrawdown = 0;
  const ordered = [...points].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  for (const point of ordered) {
    peak = Math.max(peak, point.equity);
    if (peak > 0) {
      maxDrawdown = Math.max(maxDrawdown, ((peak - point.equity) / peak) * 100);
    }
  }

  return maxDrawdown;
}

export function calculateFlowAdjustedEquity(
  points: LiveEquity[],
  initialCapital: number,
  capitalFlows: CapitalFlow[] = []
): FlowAdjustedEquity[] {
  if (!Number.isFinite(initialCapital) || initialCapital <= 0) return [];
  const ordered = [...points]
    .filter((point) => Number.isFinite(new Date(point.timestamp).getTime()))
    .sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  const flows = capitalFlows
    .filter(
      (flow) =>
        Number.isFinite(new Date(flow.timestamp).getTime()) &&
        Number.isFinite(flow.amount)
    )
    .sort(
    (a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  if (ordered.length === 0) return [];

  const result: FlowAdjustedEquity[] = [];
  let flowIndex = 0;
  let previousTime = new Date(ordered[0].timestamp).getTime();
  let previousEquity = initialCapital;
  let previousBalance = initialCapital;
  let timeWeightedEquity = initialCapital;
  let timeWeightedBalance = initialCapital;
  let peak = initialCapital;

  for (const point of ordered) {
    const time = new Date(point.timestamp).getTime();
    let flowAmount = 0;
    while (
      flowIndex < flows.length &&
      new Date(flows[flowIndex].timestamp).getTime() <= time
    ) {
      const flowTime = new Date(flows[flowIndex].timestamp).getTime();
      if (flowTime > previousTime) flowAmount += flows[flowIndex].amount;
      flowIndex += 1;
    }

    if (result.length > 0) {
      const adjustedEquityReturn =
        previousEquity > 0
          ? (point.equity - flowAmount - previousEquity) / previousEquity
          : 0;
      const adjustedBalanceReturn =
        previousBalance > 0
          ? (point.balance - flowAmount - previousBalance) / previousBalance
          : 0;
      timeWeightedEquity *= 1 + adjustedEquityReturn;
      timeWeightedBalance *= 1 + adjustedBalanceReturn;
    }

    peak = Math.max(peak, timeWeightedEquity);
    result.push({
      ...point,
      timeWeightedEquity,
      timeWeightedBalance,
      timeWeightedReturn: (timeWeightedEquity / initialCapital - 1) * 100,
      underwater:
        peak > 0
          ? -((peak - timeWeightedEquity) / peak) * 100
          : 0,
    });
    previousTime = time;
    previousEquity = point.equity;
    previousBalance = point.balance;
  }

  return result;
}

export function calculateDashboardMetrics(
  trades: LiveTrade[],
  equityPoints: LiveEquity[],
  initialCapital?: number | null,
  capitalFlows: CapitalFlow[] = []
): DashboardMetrics {
  const closed = trades.filter((trade) => trade.status === "closed");
  const openTrades = trades.filter((trade) => trade.status === "open");
  const pnlValues = closed.map((trade) => trade.pnl ?? 0);
  const wins = pnlValues.filter((pnl) => pnl > 0);
  const losses = pnlValues.filter((pnl) => pnl < 0);
  const grossProfit = wins.reduce((total, pnl) => total + pnl, 0);
  const grossLoss = Math.abs(losses.reduce((total, pnl) => total + pnl, 0));
  const meanPnl =
    pnlValues.length > 0
      ? pnlValues.reduce((total, pnl) => total + pnl, 0) / pnlValues.length
      : 0;
  const averageWin =
    wins.length > 0
      ? grossProfit / wins.length
      : null;
  const averageLoss =
    losses.length > 0
      ? grossLoss / losses.length
      : null;
  const adjustedPoints: FlowAdjustedEquity[] =
    initialCapital && initialCapital > 0
      ? calculateFlowAdjustedEquity(equityPoints, initialCapital, capitalFlows)
      : [];
  const dailyPoints = getDailyEquity(
    initialCapital && initialCapital > 0
      ? adjustedPoints.map((point) => ({
          ...point,
          equity: point.timeWeightedEquity,
        }))
      : equityPoints
  );
  const dailyReturns = dailyPoints.slice(1).flatMap((point, index) => {
    const previous = dailyPoints[index].equity;
    return previous > 0 ? [(point.equity - previous) / previous] : [];
  });
  const dailyMean =
    dailyReturns.length > 0
      ? dailyReturns.reduce((total, value) => total + value, 0) / dailyReturns.length
      : 0;
  const dailyVariance =
    dailyReturns.length > 1
      ? dailyReturns.reduce((total, value) => total + (value - dailyMean) ** 2, 0) /
        (dailyReturns.length - 1)
      : 0;
  const dailyDeviation = Math.sqrt(dailyVariance);
  const sharpeEligible = dailyReturns.length >= 30 || closed.length >= 30;
  const startPoint = dailyPoints[0];
  const endPoint = dailyPoints[dailyPoints.length - 1];
  const elapsedDays =
    startPoint && endPoint
      ? Math.max(
          (new Date(endPoint.timestamp).getTime() -
            new Date(startPoint.timestamp).getTime()) /
            86400000,
          1
        )
      : 0;
  const annualizedReturn =
    startPoint &&
    endPoint &&
    startPoint.equity > 0 &&
    endPoint.equity > 0 &&
    elapsedDays > 0
      ? (endPoint.equity / startPoint.equity) ** (365 / elapsedDays) - 1
      : null;
  const maxDrawdown =
    initialCapital && initialCapital > 0
      ? Math.max(...adjustedPoints.map((point) => -point.underwater), 0)
      : calculateMaxDrawdown(equityPoints);

  return {
    realizedPnL: pnlValues.reduce((total, pnl) => total + pnl, 0),
    winRate: closed.length > 0 ? (wins.length / closed.length) * 100 : 0,
    maxDrawdown,
    profitFactor:
      grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? null : 0,
    tradeSharpe:
      sharpeEligible && dailyDeviation > 0
        ? (dailyMean / dailyDeviation) * Math.sqrt(252)
        : null,
    calmar:
      annualizedReturn !== null && maxDrawdown > 0
        ? annualizedReturn / (maxDrawdown / 100)
        : null,
    averageRiskReward:
      averageWin !== null && averageLoss !== null && averageLoss > 0
        ? averageWin / averageLoss
        : null,
    expectancy: meanPnl,
    closedTrades: closed.length,
    openTrades: openTrades.length,
    dailyObservations: dailyReturns.length,
  };
}

export function getDailyEquity(points: LiveEquity[]) {
  const ordered = [...points].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  const byDate = new Map<string, LiveEquity>();

  for (const point of ordered) {
    const time = new Date(point.timestamp);
    if (Number.isNaN(time.getTime())) continue;
    const dateKey = `${time.getUTCFullYear()}-${time.getUTCMonth()}-${time.getUTCDate()}`;
    byDate.set(dateKey, point);
  }

  return Array.from(byDate.values());
}

export function calculateMonthlyReturns(points: LiveEquity[]): MonthlyReturn[] {
  const ordered = getDailyEquity(points);
  const byMonth = new Map<string, { year: number; month: number; opening: number; closing: number }>();
  let previousEquity: number | undefined;

  for (const point of ordered) {
    const date = new Date(point.timestamp);
    if (Number.isNaN(date.getTime())) continue;
    const year = date.getUTCFullYear();
    const month = date.getUTCMonth();
    const key = `${year}-${month}`;
    const current = byMonth.get(key);

    if (!current) {
      byMonth.set(key, {
        year,
        month,
        opening: previousEquity ?? point.equity,
        closing: point.equity,
      });
    } else {
      current.closing = point.equity;
    }
    previousEquity = point.equity;
  }

  return Array.from(byMonth.values())
    .sort((a, b) => a.year - b.year || a.month - b.month)
    .map(({ year, month, opening, closing }) => ({
      year,
      month,
      value: opening !== 0 ? ((closing - opening) / opening) * 100 : 0,
    }));
}

export function getEquityDomain(values: number[], baseline: number) {
  const minimumSpan = Math.max(Math.abs(baseline) * 0.005, 1);
  if (values.length === 0) {
    return [baseline - minimumSpan, baseline + minimumSpan] as [number, number];
  }

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  if (maximum - minimum < minimumSpan * 2) {
    const center = (minimum + maximum) / 2;
    return [center - minimumSpan, center + minimumSpan] as [number, number];
  }

  const padding = (maximum - minimum) * 0.08;
  return [minimum - padding, maximum + padding] as [number, number];
}

export function getPercentDomain(values: number[]): [number, number] {
  const minimum = Math.min(0, ...values);
  const maximum = Math.max(0, ...values);
  if (maximum - minimum <= 1) return [-0.5, 0.5];
  const padding = (maximum - minimum) * 0.08;
  return [Math.min(-0.5, minimum - padding), Math.max(0.5, maximum + padding)];
}
