"use client";

import { useEffect, useRef, type ReactNode, type RefObject } from "react";

export type TooltipPosition = {
  x: number;
  y: number;
  anchor: boolean;
};

export type TooltipPositionRef = {
  current: TooltipPosition | null;
};

export default function SmoothFollowTooltip({
  containerRef,
  targetRef,
  children,
  className = "",
  maxHeight,
  active = true,
}: {
  containerRef: RefObject<HTMLElement | null>;
  targetRef: TooltipPositionRef;
  children: ReactNode;
  className?: string;
  maxHeight?: number;
  active?: boolean;
}) {
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const tooltip = tooltipRef.current;
    const container = containerRef.current;
    if (!tooltip || !container) return;
    if (!active) {
      tooltip.style.opacity = "0";
      return;
    }

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    let displayed: { x: number; y: number } | null = null;
    let isFirstFrame = true;

    const update = () => {
      frame = 0;
      const position = targetRef.current;
      if (!position) {
        tooltip.style.opacity = "0";
        frame = requestAnimationFrame(update);
        return;
      }

      const bounds = container.getBoundingClientRect();
      const cardBounds = tooltip.getBoundingClientRect();
      const width = cardBounds.width || tooltip.offsetWidth;
      const height = cardBounds.height || tooltip.offsetHeight;
      let targetX = position.x - bounds.left;
      let targetY = position.y - bounds.top;
      if (position.anchor) {
        if (targetX + width + 12 > bounds.width) {
          targetX -= width + 12;
        } else {
          targetX += 12;
        }
        targetY -= height / 2;
      }
      targetX = Math.max(8, Math.min(targetX, bounds.width - width - 8));
      targetY = Math.max(8, Math.min(targetY, bounds.height - height - 8));

      if (isFirstFrame || reducedMotion.matches || !displayed) {
        displayed = { x: targetX, y: targetY };
        isFirstFrame = false;
      } else {
        displayed.x += (targetX - displayed.x) * 0.2;
        displayed.y += (targetY - displayed.y) * 0.2;
      }

      tooltip.style.transform = `translate3d(${displayed.x}px, ${displayed.y}px, 0)`;
      tooltip.style.opacity = "1";
      frame = requestAnimationFrame(update);
    };

    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };

    tooltip.style.opacity = "0";
    schedule();
    return () => {
      if (frame) cancelAnimationFrame(frame);
    };
  }, [active, containerRef, targetRef]);

  return (
    <div
      ref={tooltipRef}
      className={`pointer-events-none absolute left-0 top-0 z-30 chart-glass-tooltip opacity-0 transition-opacity duration-150 ${className}`}
      style={{ maxHeight, willChange: "transform, opacity" }}
    >
      {children}
    </div>
  );
}
