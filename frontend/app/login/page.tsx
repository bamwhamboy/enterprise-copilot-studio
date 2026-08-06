"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Sparkles,
  Loader2,
  AlertCircle,
  Mail,
  Lock,
  ShieldCheck,
  Workflow,
  Database,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { login, fetchCurrentUser } from "@/lib/api/auth";
import { useAuthStore } from "@/store/auth-store";
import type { ApiError } from "@/services/api-client";

const highlights = [
  {
    icon: Workflow,
    title: "LangGraph-orchestrated copilots",
    description: "Multi-step retrieval, grounding, and citation in one workflow.",
  },
  {
    icon: Database,
    title: "Hybrid Hierarchical RAG",
    description: "Semantic + BM25 retrieval over your enterprise knowledge.",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise-grade security",
    description: "JWT auth, role-based access, and organization isolation.",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const tokens = await login({ email, password });
      setTokens(tokens, rememberMe);
      const user = await fetchCurrentUser();
      setUser(user);
      router.push("/");
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError?.message || "Something went wrong. Please try again.");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
      {/* Branding panel */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-[#1a1730] via-[#221c42] to-[#171325] lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="pointer-events-none absolute inset-0 opacity-40">
          <div className="absolute -top-24 -left-24 size-96 rounded-full bg-primary/30 blur-3xl" />
          <div className="absolute -bottom-32 -right-16 size-96 rounded-full bg-[#5b7cfa]/30 blur-3xl" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative flex items-center gap-2.5"
        >
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-[#5b7cfa] shadow-lg shadow-primary/30">
            <Sparkles className="size-[18px] text-primary-foreground" />
          </div>
          <span className="text-base font-semibold tracking-tight text-white">
            Enterprise Copilot Studio
          </span>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="relative flex flex-col gap-10"
        >
          <div>
            <h1 className="max-w-md text-3xl font-semibold leading-tight tracking-tight text-white">
              Compose and deploy AI copilots your whole organization can trust.
            </h1>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/60">
              One platform for retrieval-grounded chat, knowledge management, and
              enterprise-grade governance — built on your own data.
            </p>
          </div>

          <div className="flex flex-col gap-5">
            {highlights.map((item, index) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.2 + index * 0.08 }}
                className="flex items-start gap-3.5"
              >
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-white/10 text-white backdrop-blur-sm">
                  <item.icon className="size-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{item.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-white/50">
                    {item.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <p className="relative text-xs text-white/35">
          © {new Date().getFullYear()} Enterprise Copilot Studio. All rights reserved.
        </p>
      </div>

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

          <p className="mt-8 text-center text-xs text-muted-foreground">
            Don&apos;t have an account? Ask your organization admin to invite you,
            or register a new organization via the API&apos;s{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">
              /auth/register
            </code>{" "}
            endpoint.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
