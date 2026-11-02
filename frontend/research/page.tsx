import type { Metadata } from "next";

const title = "Data Mining and Machine Learning";
const description =
  "See how GenX by Vortech Markets presents feature engineering, market-regime detection, trade prediction, and model explanations for quantitative research.";

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: "/research",
  },
  openGraph: {
    type: "website",
    title,
    description,
    url: "/research",
  },
  twitter: {
    card: "summary",
    title,
    description,
  },
};

const CARDS = [
  { icon: "🔧", title: "Feature Engineering", desc: "60+ features from OHLC and trade logs: volatility, trend, regime, DNA, and strategy parameters." },
  { icon: "🌊", title: "Regime Detection", desc: "Five market regimes classified per cycle: strong trend up/down, weak trend, ranging, and high volatility." },
  { icon: "🧠", title: "Win Predictor", desc: "Random Forest classifiers trained per symbol predict win probability before trade execution." },
  { icon: "🔍", title: "SHAP Explanations", desc: "Every rejected trade has a SHAP breakdown showing which features drove the decision." },
  { icon: "📈", title: "Surrogate Models", desc: "ML surrogates on GA logs predict fitness, cutting optimisation time up to 5×." },
  { icon: "🛡️", title: "Audit Suite", desc: "Every session audited for execution integrity, data quality, and risk constraints." },
];

export default function ResearchPage() {
  return (
    <main className="min-h-screen">
      <section className="px-6 py-20 text-center">
        <span className="text-xs font-semibold text-[#10B981] uppercase tracking-widest">
          Research
        </span>
        <h1 className="text-5xl font-bold mt-4 mb-6">Data Mining & Machine Learning</h1>
        <p className="text-xl text-slate-400 max-w-3xl mx-auto">
          Feature engineering, regime detection, win prediction, and SHAP-based
          explanations — all running on the GenX trade database.
        </p>
      </section>

      <section className="px-6 py-12 max-w-6xl mx-auto">
        <div className="grid md:grid-cols-3 gap-6">
          {CARDS.map((c) => (
            <div key={c.title} className="card text-center">
              <div className="text-4xl mb-4">{c.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{c.title}</h3>
              <p className="text-sm text-slate-400">{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

    </main>
  );
}