import type { MinuteMarketSource } from "@/lib/vtgxDatafeed";

export const realProvider: MinuteMarketSource = {
  // Replace this pre-launch stub with the listing venue's minute-bar API and live stream.
  async getBars() {
    return [];
  },
  subscribeBars() {
    return () => {};
  },
};
