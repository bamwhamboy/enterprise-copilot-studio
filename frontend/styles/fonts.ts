import { Geist, Geist_Mono } from "next/font/google";

/**
 * Primary UI typeface. Geist reads clean and enterprise-grade,
 * matching the Vercel / Linear inspired design language.
 */
export const fontSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

/**
 * Monospace typeface for metrics, code, and tabular figures
 * (cost values, request counts, IDs).
 */
export const fontMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});
