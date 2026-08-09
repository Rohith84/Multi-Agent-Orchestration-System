/**
 * useInView — Lightweight Intersection Observer hook for scroll-triggered animations.
 *
 * Returns a ref and a boolean indicating whether the element is in the viewport.
 * Respects prefers-reduced-motion by immediately reporting as visible.
 */

"use client";

import { useRef, useState, useEffect } from "react";

interface UseInViewOptions {
  /** Percentage of element that must be visible (0–1). Default: 0.15 */
  threshold?: number;
  /** Only trigger once. Default: true */
  triggerOnce?: boolean;
  /** Root margin. Default: "0px 0px -60px 0px" */
  rootMargin?: string;
}

export function useInView(options: UseInViewOptions = {}) {
  const { threshold = 0.15, triggerOnce = true, rootMargin = "0px 0px -60px 0px" } = options;
  const ref = useRef<HTMLElement | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    // Respect reduced motion — show everything immediately
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setInView(true);
      return;
    }

    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (triggerOnce) {
            observer.unobserve(element);
          }
        } else if (!triggerOnce) {
          setInView(false);
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [threshold, triggerOnce, rootMargin]);

  return { ref, inView };
}
