import {
  createDemoAccountProvider,
  DemoAccountControls,
  DemoAccountBanner,
} from "@/lib/datafeed/demo/demoAccountProvider";

export function loadDemoProvider(fixtureId: string) {
  return {
    provider: createDemoAccountProvider(fixtureId),
    DemoAccountControls,
    DemoAccountBanner,
  };
}
