import Link from "next/link";

const groups = [
  {
    title: "Platform",
    links: [
      { href: "/vision", label: "Vision" },
      { href: "/strategies", label: "Strategies" },
      { href: "/research", label: "Research" },
    ],
  },
  {
    title: "Workspace",
    links: [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/dashboard/billing", label: "Billing" },
      { href: "/login", label: "Sign in" },
    ],
  },
  {
    title: "Vortech Markets",
    links: [
      { href: "https://vortech.markets/about.html", label: "About Us" },
      { href: "https://vortech.markets/market-research.html", label: "Market Research" },
      { href: "https://vortech.markets/contact.html", label: "Contact" },
    ],
  },
  {
    title: "Legal",
    links: [
      { href: "https://vortech.markets/privacy-policy.html", label: "Privacy Policy" },
      { href: "https://vortech.markets/terms.html", label: "Terms & Conditions" },
      { href: "https://vortech.markets/risk-disclosure.html", label: "Risk Disclosures" },
    ],
  },
];

export default function InstitutionalFooter() {
  return (
    <footer className="institutional-footer border-t border-slate-800/80 px-6 pb-[calc(6rem+env(safe-area-inset-bottom))] pt-14">
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-2 gap-10 border-b border-slate-800/80 pb-10 lg:grid-cols-5">
          <div className="col-span-2 lg:col-span-1">
            <Link href="/" className="inline-flex items-center gap-2 text-lg font-semibold">
              <span className="text-xl" aria-hidden="true">🧬</span>
              <span className="gradient-text">GenX</span>
            </Link>
            <div className="mt-5 space-y-2 text-sm text-slate-400">
              <a href="mailto:contact@vortech.markets">contact@vortech.markets</a>
              <p>
                <a
                  href="https://wa.me/243832082287"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  +243 832 082 287
                </a>
              </p>
              <p>Kinshasa, DRC</p>
            </div>
          </div>

          <div className="col-span-1 grid content-start gap-10 lg:contents">
            {groups.slice(0, 2).map((group) => (
              <nav key={group.title} aria-label={group.title}>
                <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                  {group.title}
                </h2>
                <ul className="space-y-3 text-sm text-slate-500">
                  {group.links.map((link) => {
                    const external = link.href.startsWith("https://");
                    return (
                      <li key={link.href}>
                        {external ? (
                          <a href={link.href} target="_blank" rel="noopener noreferrer">
                            {link.label}
                          </a>
                        ) : (
                          <Link href={link.href}>{link.label}</Link>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </nav>
            ))}
          </div>
          <div className="col-span-1 grid content-start gap-10 lg:contents">
            {groups.slice(2).map((group) => (
              <nav key={group.title} aria-label={group.title}>
                <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                  {group.title}
                </h2>
                <ul className="space-y-3 text-sm text-slate-500">
                  {group.links.map((link) => (
                    <li key={link.href}>
                      <a href={link.href} target="_blank" rel="noopener noreferrer">
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        </div>

        <p className="max-w-5xl py-6 text-xs leading-6 text-slate-500">
          Financial markets involve inherent risks of capital loss. Market intelligence,
          research briefings, institutional insights, analytical models, and technological
          frameworks provided by Vortech Markets are intended strictly for analytical,
          educational, operational, and informational purposes under agreed client mandates.
          Nothing contained within this platform or associated private networks constitutes
          personalized investment advice, financial advisory, a solicitation of funds, or
          automated execution signals. Vortech Markets operates as a technology provider,
          multi-asset trading infrastructure developer, and Introducing Broker; it does not
          offer direct custodial brokerage services or discretionary portfolio management.
          Access to private channels and high-touch OTC desk execution is subject to client
          eligibility, risk verification, and compliance onboarding.
        </p>
        <div className="pt-4 text-right text-xs text-slate-500">
          © {new Date().getFullYear()} Vortech Markets. All Rights Reserved.
        </div>
      </div>
    </footer>
  );
}
