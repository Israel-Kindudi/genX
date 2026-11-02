import {
  createSnapshotAccountProvider,
  type AccountDataProvider,
  type AccountDataSnapshot,
  type DemoBannerComponent,
  type DemoControlsComponent,
} from "@/lib/accountDataProvider";

export async function createAccountDataProvider(
  liveSnapshot: AccountDataSnapshot
): Promise<{
  provider: AccountDataProvider;
  DemoAccountControls: DemoControlsComponent | null;
  DemoAccountBanner: DemoBannerComponent | null;
}> {
  if (
    process.env.NODE_ENV === "development" &&
    process.env.NEXT_PUBLIC_ACCOUNT_DATA_PROVIDER !== "live"
  ) {
    return loadDemoProvider(process.env.NEXT_PUBLIC_ACCOUNT_DATA_PROVIDER ?? "");
  }

  return {
    provider: createSnapshotAccountProvider(liveSnapshot),
    DemoAccountControls: null,
    DemoAccountBanner: null,
  };
}

async function loadDemoProvider(fixtureId: string) {
  const developmentProvider = await import("@/lib/accountDataProviderDevelopment");
  return developmentProvider.loadDemoProvider(fixtureId);
}
