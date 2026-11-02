let activeCancel: (() => void) | null = null;

export function cancelScrollToTop() {
  activeCancel?.();
}

export function scrollToTop() {
  cancelScrollToTop();

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    window.scrollTo(0, 0);
    return;
  }

  const startY = window.scrollY;
  if (startY <= 0) return;

  const duration = Math.min(1100, Math.max(900, 900 + startY / 100));
  const startTime = performance.now();
  let frame = 0;
  let finished = false;

  const cleanup = () => {
    if (finished) return;
    finished = true;
    if (frame) cancelAnimationFrame(frame);
    window.removeEventListener("wheel", cleanup);
    window.removeEventListener("touchstart", cleanup);
    window.removeEventListener("keydown", cleanup);
    if (activeCancel === cleanup) activeCancel = null;
  };
  activeCancel = cleanup;

  window.addEventListener("wheel", cleanup, { passive: true });
  window.addEventListener("touchstart", cleanup, { passive: true });
  window.addEventListener("keydown", cleanup);

  const animate = (now: number) => {
    if (finished) return;
    const progress = Math.min(1, (now - startTime) / duration);
    const eased = progress < 0.5
      ? 4 * progress * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 3) / 2;
    window.scrollTo(0, startY * (1 - eased));

    if (progress < 1) {
      frame = requestAnimationFrame(animate);
    } else {
      cleanup();
      window.scrollTo(0, 0);
    }
  };

  frame = requestAnimationFrame(animate);
}
