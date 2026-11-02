import type { CapitalFlow, LiveEquity, LiveTrade } from "@/lib/useLiveTrades";

export type AccountDataSnapshot = {
  initialCapital: number | null;
  currency: string | null;
  equityPoints: LiveEquity[];
  trades: LiveTrade[];
  capitalFlows: CapitalFlow[];
  connected: boolean;
  isDemonstration: boolean;
  fixtureId?: string;
};

export interface AccountDataProvider {
  getSnapshot(): AccountDataSnapshot;
  subscribe(listener: () => void): () => void;
  selectFixture?(fixtureId: string): void;
  dispose?(): void;
}

export type DemoControlsComponent = React.ComponentType<{
  fixtureId: string;
  onSelect: (fixtureId: string) => void;
}>;

export type DemoBannerComponent = React.ComponentType;

export function createSnapshotAccountProvider(
  snapshot: AccountDataSnapshot
): AccountDataProvider {
  return {
    getSnapshot: () => snapshot,
    subscribe: () => () => {},
  };
}
