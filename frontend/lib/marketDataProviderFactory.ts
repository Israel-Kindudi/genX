import {
  createMarketDataProvider as createSharedProvider,
  type MarketDataProvider,
} from "@/lib/vtgxDatafeed";
import { realProvider } from "@/lib/datafeed/real/realProvider";

export type MarketProviderSelection = "real" | "mock";

export async function createMarketDataProvider(
  selection: MarketProviderSelection =
    process.env.NEXT_PUBLIC_MARKET_DATA_PROVIDER === "mock" ? "mock" : "real"
): Promise<MarketDataProvider> {
  if (selection === "mock" && process.env.NODE_ENV === "development") {
    const { createMockProvider } = await import(
      "@/lib/datafeed/mock/mockProvider"
    );
    return createSharedProvider({
      mode: "minute-only",
      source: createMockProvider(),
    });
  }

  return createSharedProvider({
    mode: "minute-only",
    source: realProvider,
  });
}
