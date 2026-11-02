"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createSnapshotAccountProvider,
  type AccountDataProvider,
  type DemoBannerComponent,
  type DemoControlsComponent,
} from "@/lib/accountDataProvider";
import { createAccountDataProvider } from "@/lib/accountDataProviderFactory";
import { useLiveTrades } from "@/lib/useLiveTrades";

export function useAccountDataProvider() {
  const demoEnabled =
    process.env.NODE_ENV === "development" &&
    process.env.NEXT_PUBLIC_ACCOUNT_DATA_PROVIDER !== "live";
  const live = useLiveTrades(5000, 10000, !demoEnabled);
  const [demoProvider, setDemoProvider] = useState<AccountDataProvider | null>(null);
  const [DemoAccountControls, setDemoAccountControls] =
    useState<DemoControlsComponent | null>(null);
  const [DemoAccountBanner, setDemoAccountBanner] =
    useState<DemoBannerComponent | null>(null);
  const [, setProviderRevision] = useState(0);
  const liveProvider = useMemo(
    () =>
      createSnapshotAccountProvider({
        initialCapital: live.initialCapital,
        currency: live.currency,
        equityPoints: live.equityPoints,
        trades: live.trades,
        capitalFlows: live.capitalFlows,
        connected: live.connected,
        isDemonstration: false,
      }),
    [
      live.initialCapital,
      live.currency,
      live.equityPoints,
      live.trades,
      live.capitalFlows,
      live.connected,
    ]
  );

  useEffect(() => {
    if (
      process.env.NODE_ENV !== "development" ||
      process.env.NEXT_PUBLIC_ACCOUNT_DATA_PROVIDER === "live"
    ) {
      return;
    }

    let active = true;
    let unsubscribe = () => {};
    let createdProvider: AccountDataProvider | null = null;
    createAccountDataProvider(liveProvider.getSnapshot())
      .then(({ provider, DemoAccountControls: Controls, DemoAccountBanner: Banner }) => {
        if (!active) {
          provider.dispose?.();
          return;
        }
        createdProvider = provider;
        unsubscribe = provider.subscribe(() => {
          setProviderRevision((revision) => revision + 1);
        });
        setDemoProvider(provider);
        setDemoAccountControls(() => Controls);
        setDemoAccountBanner(() => Banner);
      })
      .catch((error: unknown) => {
        console.error("Unable to initialize the development account provider.", error);
      });

    return () => {
      active = false;
      unsubscribe();
      createdProvider?.dispose?.();
    };
  }, []);

  const provider = demoProvider ?? liveProvider;
  return {
    provider,
    snapshot: provider.getSnapshot(),
    DemoAccountControls,
    DemoAccountBanner,
  };
}
