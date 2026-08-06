"use client";

import { useEffect, useRef, useState } from "react";
import { animate } from "framer-motion";

/**
 * Animates a count-up whenever `value` is a parseable number (real
 * dashboard stats -- counts of copilots, sources, documents, etc).
 * Non-numeric values (like the "—" loading placeholder) are derived
 * directly during render -- no state or effect needed for that case,
 * only the animated (numeric) path legitimately synchronizes with an
 * external system (framer-motion's animation loop) via an effect.
 */
export function AnimatedCounter({ value }: { value: string }) {
  const numericValue = Number(value);
  const isNumeric = value.trim() !== "" && !Number.isNaN(numericValue);
  const [animatedDisplay, setAnimatedDisplay] = useState("0");
  const prevValueRef = useRef(0);

  useEffect(() => {
    if (!isNumeric) return;
    const controls = animate(prevValueRef.current, numericValue, {
      duration: 0.6,
      ease: "easeOut",
      onUpdate: (latest) => setAnimatedDisplay(String(Math.round(latest))),
    });
    prevValueRef.current = numericValue;
    return () => controls.stop();
  }, [isNumeric, numericValue]);

  if (!isNumeric) return <>{value}</>;
  return <>{animatedDisplay}</>;
}
