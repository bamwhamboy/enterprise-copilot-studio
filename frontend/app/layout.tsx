import type { Metadata } from "next";

import { fontSans, fontMono } from "@/styles/fonts";
import { Providers } from "@/components/layout/providers";
import { AppShell } from "@/components/layout/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Enterprise Copilot Studio",
  description:
    "Compose, deploy, and manage enterprise AI copilots from reusable AI components.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${fontSans.variable} ${fontMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
