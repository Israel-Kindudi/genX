import type { Metadata } from "next";
import Link from "next/link";
import PricingSection from "@/components/PricingSection";
import GenXDNACanvas from "@/components/GenXDNACanvas";

const title = "Gen X Engine | Quantitative Trading Platform by Vortech Markets";
const description =
  "Discover GenX by Vortech Markets: a quantitative trading research engine combining Market DNA, statistical fitness, backtesting, and genetic strategy optimisation.";

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    title,
    description,
    url: "/",
  },
  twitter: {
    card: "summary",
    title,
    description,
  },
};

const softwareApplicationStructuredData = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "@id": "https://genx.vortech.markets/#software",
  name: "GenX",
  url: "https://genx.vortech.markets/",
  description,
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  publisher: { "@id": "https://vortech.markets/#organization" },
  featureList: [
    "Market DNA statistical analysis",
    "Quantitative trading strategy research",
    "Backtesting and genetic optimisation",
  ],
};

export default function Home() {
  return (
    <main className="min-h-screen">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(softwareApplicationStructuredData).replace(
            /</g,
            "\\u003c"
          ),
        }}
      />
      <section className="genx-hero">
        <div className="genx-hero-shell">
          <header className="genx-hero-copy">
            <span className="genx-hero-eyebrow">
              <span className="genx-hero-indicator" aria-hidden="true" />
              Quantitative Trading Platform
            </span>
            <h1>
              Where Markets
              <br />
              Meet <span className="gradient-text">Genetics</span>
            </h1>
            <p className="genx-hero-lede">
              GenX models each market as a chromosome-like data structure, the
              Market DNA, and evolves strategy parameters with a genetic
              algorithm guided by statistical fitness.
            </p>
            <div className="genx-hero-actions">
              <Link href="/vision" className="btn-primary">
                Explore the vision
              </Link>
              <Link href="/dashboard" className="btn-ghost">
                View dashboard
              </Link>
            </div>
            <div className="genx-hero-stats">
              <div className="genx-hero-stat">
                <div className="genx-hero-stat-value">8</div>
                <div className="genx-hero-stat-label">DNA chromosomes</div>
              </div>
              <div className="genx-hero-stat">
                <div className="genx-hero-stat-value">10+</div>
                <div className="genx-hero-stat-label">Strategies</div>
              </div>
              <div className="genx-hero-stat">
                <div className="genx-hero-stat-value">GA</div>
                <div className="genx-hero-stat-label">Optimisation</div>
              </div>
            </div>
          </header>

          <div className="genx-hero-visual">
            <div className="genx-hero-visual-index" aria-hidden="true">
              <span>GX / 01</span>
              <span>GENETIC SYSTEMS</span>
            </div>
            <div className="genx-hero-readout genx-hero-readout-top" aria-hidden="true">
              <span className="genx-hero-readout-label">MARKET DNA</span>
              <span className="genx-hero-readout-value">08 CHROMOSOMES</span>
            </div>
            <GenXDNACanvas />
            <div className="genx-hero-readout genx-hero-readout-bottom" aria-hidden="true">
              <span className="genx-hero-readout-label">GENETIC OPTIMISATION</span>
              <span className="genx-hero-readout-value">GA / STATISTICAL FITNESS</span>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 py-24">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-xs font-semibold text-[#10B981] uppercase tracking-widest">
              The Framework
            </span>
            <h2 className="text-4xl font-bold mt-3 mb-4">
              Four pillars of GenX
            </h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Every decision in GenX is driven by the intersection of market
              structure, statistical rigor, evolutionary search, and live
              execution.
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              {
                icon: "🧬",
                title: "Market DNA",
                text: "Eight statistical chromosomes capture volatility, momentum, structure, and more.",
              },
              {
                icon: "📊",
                title: "Fast Backtester",
                text: "Vectorized backtests with pre-computed indicators; thousands of combos in minutes.",
              },
              {
                icon: "🎯",
                title: "Genetic Optimisation",
                text: "DNA-guided genetic algorithms evolve parameters using Sharpe, PnL, and win rate.",
              },
              {
                icon: "🚀",
                title: "Live Trading",
                text: "MT5 integration with regime detection, breakeven logic, and ML filtering.",
              },
            ].map((c) => (
              <div key={c.title} className="card text-center">
                <div className="text-4xl mb-4">{c.icon}</div>
                <h3 className="text-lg font-semibold mb-2">{c.title}</h3>
                <p className="text-sm text-slate-400">{c.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <PricingSection />
    </main>
  );
}