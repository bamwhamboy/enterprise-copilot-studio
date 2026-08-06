"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, Loader2, AlertCircle, CheckCircle2, Mail, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { login, fetchCurrentUser } from "@/lib/api/auth";
import { useAuthStore } from "@/store/auth-store";
import type { ApiError } from "@/services/api-client";
import { AuthBrandingPanel } from "@/components/auth/auth-branding-panel";
import { AuthLoadingScreen } from "@/components/auth/auth-loading-screen";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const accessToken = useAuthStore((s) => s.accessToken);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Shown when arriving here after a successful registration whose
  // auto-login step didn't complete (see app/register/page.tsx) -- the
  // account genuinely exists, this is just a graceful fallback to
  // finish signing in manually rather than an error.
  const justRegistered = searchParams.get("registered") === "1";

  useEffect(() => {
    if (hasHydrated && accessToken) {
      router.replace("/");
    }
  }, [hasHydrated, accessToken, router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const tokens = await login({ email, password });
      setTokens(tokens, rememberMe);
      const user = await fetchCurrentUser();
      setUser(user);
      router.replace("/");
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError?.message || "Something went wrong. Please try again.");
      setIsSubmitting(false);
    }
  }

  // Not yet hydrated (can't know auth state yet), or already
  // authenticated and about to redirect away -- show a neutral loading
  // state instead of ever flashing the login form.
  if (!hasHydrated || accessToken) {
    return <AuthLoadingScreen />;
  }

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
      <AuthBrandingPanel headline="Compose and deploy AI copilots your whole organization can trust." />

      {/* Login form panel */}
      <div className="flex items-center justify-center bg-background px-6 py-12 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          <div className="mb-8 flex flex-col items-center gap-3 text-center lg:hidden">
            <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/25">
              <Sparkles className="size-5 text-primary-foreground" />
            </div>
            <span className="text-base font-semibold tracking-tight text-foreground">
              Enterprise Copilot Studio
            </span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              Welcome back
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Sign in to access your copilots and knowledge sources.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
            {justRegistered && !error && (
              <div
                role="status"
                className="flex items-start gap-2.5 rounded-lg border border-success/20 bg-success/5 px-3.5 py-3 text-sm text-success"
              >
                <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                <span>Account created successfully. Please sign in.</span>
              </div>
            )}

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-lg border border-destructive/20 bg-destructive/5 px-3.5 py-3 text-sm text-destructive"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Work email</Label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  className="pl-9"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <button
                  type="button"
                  className="text-xs font-medium text-primary hover:underline"
                  onClick={() =>
                    setError(
                      "Password reset isn't available yet — contact your organization admin."
                    )
                  }
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="pl-9"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked === true)}
                disabled={isSubmitting}
              />
              <Label htmlFor="remember-me" className="cursor-pointer font-normal text-muted-foreground">
                Remember me on this device
              </Label>
            </div>

            <Button type="submit" size="lg" className="mt-1 w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="font-medium text-primary hover:underline">
              Create one
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
