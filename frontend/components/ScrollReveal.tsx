"use client";

import { useEffect } from "react";

const REVEAL_SELECTOR =
  "main section:not(.pricing-section), main .card, main table, main table tbody tr, main [data-reveal], main > div > div";

export default function ScrollReveal({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const observed = new WeakSet<Element>();
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
    );

    const observeElements = (root: ParentNode) => {
      root.querySelectorAll(REVEAL_SELECTOR).forEach((element) => {
        if (observed.has(element)) return;
        observed.add(element);
        element.classList.add("scroll-reveal");
        const parent = element.parentElement;
        const siblings = parent
          ? Array.from(parent.children).filter((child) =>
              child.matches(REVEAL_SELECTOR)
            )
          : [];
        const stagger = Math.min(Math.max(siblings.indexOf(element), 0), 5);
        element.setAttribute("data-reveal-delay", String(stagger));
        revealObserver.observe(element);
      });
    };

    document.documentElement.classList.add("motion-ready");
    observeElements(document);

    const mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node instanceof HTMLElement) {
            if (node.matches(REVEAL_SELECTOR)) {
              observeElements(node.parentElement ?? document);
            } else {
              observeElements(node);
            }
          }
        });
      });
    });
    mutationObserver.observe(document.body, { childList: true, subtree: true });

    return () => {
      mutationObserver.disconnect();
      revealObserver.disconnect();
      document.documentElement.classList.remove("motion-ready");
    };
  }, []);

  return <>{children}</>;
}
