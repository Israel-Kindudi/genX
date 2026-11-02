import type { Metadata } from "next";

const title = "The GenX Vision";
const description =
  "Learn how GenX by Vortech Markets models financial markets through eight statistical Market DNA chromosomes and evolves strategies to match each instrument.";

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: "/vision",
  },
  openGraph: {
    type: "website",
    title,
    description,
    url: "/vision",
  },
  twitter: {
    card: "summary",
    title,
    description,
  },
};

export default function VisionPage() {
  return (
    <main className="min-h-screen">
      <section className="px-6 py-20 text-center">
        <span className="text-xs font-semibold text-[#10B981] uppercase tracking-widest">
          Methodology
        </span>
        <h1 className="text-5xl font-bold mt-4 mb-6">The GenX Vision</h1>
        <p className="text-xl text-slate-400 max-w-3xl mx-auto">
          A framework that treats financial markets as living systems with genetic
          code, evolving strategies to match each instrument&apos;s statistical signature.
        </p>
      </section>

      <section className="px-6 py-16 max-w-3xl mx-auto">
        <h2 className="text-3xl font-bold mt-12 mb-4">Why genetics?</h2>
        <p className="text-slate-400 text-lg mb-4">
          Markets are not random walks. They exhibit persistent statistical structures,
          including volatility clustering, momentum, mean reversion, and fractal
          dimensions, that can be described, measured, and exploited.
        </p>
        <p className="text-slate-400 text-lg mb-4">
          GenX&apos;s hypothesis is that each market has a unique{" "}
          <strong className="text-white">DNA</strong>: a fixed-length vector of eight
          statistical chromosomes that summarises its behaviour. Strategies that match
          the DNA have higher expected success rates.
        </p>

        <h2 className="text-3xl font-bold mt-12 mb-6">The eight chromosomes</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {[
            { num: "I", name: "Volatility", text: "Short and long-term realised volatility, ATR." },
            { num: "II", name: "Persistence", text: "Hurst exponent, autocorrelation." },
            { num: "III", name: "Volume Bias", text: "Directional volume pressure." },
            { num: "IV", name: "Correlation", text: "Cross-asset dependencies." },
            { num: "V", name: "Fractal Structure", text: "Fractal dimension, self-similarity." },
            { num: "VI", name: "Regime", text: "Trending, ranging, or volatile state." },
            { num: "VII", name: "Efficiency", text: "Market efficiency ratio, entropy." },
            { num: "VIII", name: "Stability", text: "Stationarity, structural breaks." },
          ].map((c) => (
            <div key={c.num} className="card relative">
              <div
                className="absolute -top-3 left-4 px-2 py-0.5 rounded-full text-xs font-bold text-black"
                style={{ background: "linear-gradient(135deg, #10B981, #34D399)" }}
              >
                {c.num}
              </div>
              <h3 className="text-lg font-semibold mb-2">{c.name}</h3>
              <p className="text-sm text-slate-400">{c.text}</p>
            </div>
          ))}
        </div>
      </section>

    </main>
  );
}