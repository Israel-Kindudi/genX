"use client";

import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";
import { scrollToTop } from "@/lib/scrollToTop";

export default function BackToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let frame = 0;
    let isVisible = window.scrollY > 400;

    const updateVisibility = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        const scrollY = window.scrollY;
        if (isVisible ? scrollY < 300 : scrollY >= 400) {
          isVisible = !isVisible;
          setVisible(isVisible);
        }
        frame = 0;
      });
    };

    setVisible(isVisible);
    window.addEventListener("scroll", updateVisibility, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", updateVisibility);
    };
  }, []);

  return (
    <div
      aria-hidden={!visible}
      className={`pointer-events-none fixed bottom-6 right-6 z-[110] pb-[env(safe-area-inset-bottom)] transition-all duration-300 ${
        visible
          ? "translate-y-0 opacity-100"
          : "translate-y-4 opacity-0"
      }`}
    >
      <button
        type="button"
        aria-label="Retour en haut"
        tabIndex={visible ? 0 : -1}
        onClick={scrollToTop}
        className="pointer-events-auto flex h-11 w-11 items-center justify-center rounded-full border border-emerald-400/40 bg-[#111723]/95 text-emerald-300 shadow-lg shadow-emerald-500/10 transition-all duration-300 hover:-translate-y-1 hover:border-emerald-300 hover:bg-emerald-500/15 hover:text-emerald-200 hover:shadow-emerald-500/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0B0F17]"
      >
        <ArrowUp size={18} aria-hidden="true" />
      </button>
    </div>
  );
}
