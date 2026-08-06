"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, Loader2, AlertCircle, Mail, Lock, User, Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login, register, fetchCurrentUser } from "@/lib/api/auth";
import { useAuthStore } from "@/store/auth-store";
import { generateWorkspaceName } from "@/lib/workspace-name";
import { cn } from "@/lib/utils";
import type { ApiError } from "@/services/api-client";
import { AuthBrandingPanel } from "@/components/auth/auth-branding-panel";
import { AuthLoadingScreen } from "@/components/auth/auth-loading-screen";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8; // matches the backend's UserRegister schema exactly
const MAX_PASSWORD_LENGTH = 72; // bcrypt's own hard limit, same as the backend enforces

interface FieldErrors {
  fullName?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

function passwordStrength(password: string): { label: string; className: string; score: number } {
  if (!password) return { label: "", className: "", score: 0 };
  let score = 0;
  if (password.length >= MIN_PASSWORD_LENGTH) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password) || /[^A-Za-z0-9]/.test(password)) score++;

  if (score <= 1) return { label: "Weak", className: "bg-destructive text-destructive", score };
  if (score <= 2) return { label: "Fair", className: "bg-warning text-warning", score };
  if (score === 3) return { label: "Good", className: "bg-primary text-primary", score };
  return { label: "Strong", className: "bg-success text-success", score };
}

export default function RegisterPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const accessToken = useAuthStore((s) => s.accessToken);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    if (hasHydrated && accessToken) {
      router.replace("/");
    }
  }, [hasHydrated, accessToken, router]);

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    if (!fullName.trim()) {
      errors.fullName = "Enter your full name.";
    }
    if (!email.trim()) {
      errors.email = "Enter your email address.";
    } else if (!EMAIL_PATTERN.test(email.trim())) {
      errors.email = "Enter a valid email address.";
    }
    if (!password) {
      errors.password = "Choose a password.";
    } else if (password.length < MIN_PASSWORD_LENGTH) {
      errors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    } else if (password.length > MAX_PASSWORD_LENGTH) {
      errors.password = `Password must be at most ${MAX_PASSWORD_LENGTH} characters.`;
    }
    if (!confirmPassword) {
      errors.confirmPassword = "Confirm your password.";
    } else if (confirmPassword !== password) {
      errors.confirmPassword = "Passwords don't match.";
    }
    return errors;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setServerError(null);

    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);
    try {
      await register({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        // Every account gets its own private, isolated workspace --
        // never derived from the email domain (most users register with
        // personal providers like Gmail/Outlook, which would otherwise
        // incorrectly group unrelated strangers into one organization).
        // See lib/workspace-name.ts for why the uniqueness suffix is
        // required, not cosmetic.
        organization_name: generateWorkspaceName(fullName.trim()),
      });
    } catch (err) {
      const apiError = err as ApiError;
      setServerError(apiError?.message || "Something went wrong. Please try again.");
      setIsSubmitting(false);
      return;
    }

    // Registration succeeded. Preferred flow: log the user in
    // immediately and land them in the Dashboard, reusing the exact
    // same login + fetchCurrentUser calls the Login page itself uses.
    try {
      const tokens = await login({ email: email.trim(), password });
      setTokens(tokens, true);
      const user = await fetchCurrentUser();
      setUser(user);
      router.replace("/");
    } catch {
      // The account genuinely exists at this point -- a hiccup in the
      // auto-login step shouldn't look like a failure. Fall back to a
      // manual sign-in with a clear success message instead of an error.
      router.push("/login?registered=1");
    }
  }

  if (!hasHydrated || accessToken) {
    return <AuthLoadingScreen />;
  }

  const strength = passwordStrength(password);

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
      <AuthBrandingPanel headline="Your own AI workspace, grounded in your organization's knowledge." />

      {/* Register form panel */}
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
              Create your account
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Get your own workspace and start building copilots in minutes.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
            {serverError && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-lg border border-destructive/20 bg-destructive/5 px-3.5 py-3 text-sm text-destructive"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{serverError}</span>
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Label htmlFor="fullName">Full name</Label>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="fullName"
                  type="text"
                  autoComplete="name"
                  placeholder="Jane Doe"
                  className="pl-9"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={isSubmitting}
                  aria-invalid={Boolean(fieldErrors.fullName)}
                />
              </div>
              {fieldErrors.fullName && (
                <p className="text-xs text-destructive">{fieldErrors.fullName}</p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email address</Label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  className="pl-9"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                  aria-invalid={Boolean(fieldErrors.email)}
                />
              </div>
              {fieldErrors.email && <p className="text-xs text-destructive">{fieldErrors.email}</p>}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="At least 8 characters"
                  className="pl-9"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  aria-invalid={Boolean(fieldErrors.password)}
                />
              </div>
              {password && !fieldErrors.password && (
                <div className="flex items-center gap-2">
                  <div className="flex h-1 flex-1 gap-1">
                    {[0, 1, 2, 3].map((i) => (
                      <span
                        key={i}
                        className={cn(
                          "h-full flex-1 rounded-full bg-muted",
                          i < strength.score && strength.className.split(" ")[0]
                        )}
                      />
                    ))}
                  </div>
                  <span
                    className={cn(
                      "text-[11px] font-medium",
                      strength.className.split(" ")[1] || "text-muted-foreground"
                    )}
                  >
                    {strength.label}
                  </span>
                </div>
              )}
              {fieldErrors.password && (
                <p className="text-xs text-destructive">{fieldErrors.password}</p>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Re-enter your password"
                  className="pl-9"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                  aria-invalid={Boolean(fieldErrors.confirmPassword)}
                />
                {confirmPassword && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    {confirmPassword === password ? (
                      <Check className="size-4 text-success" />
                    ) : (
                      <X className="size-4 text-destructive" />
                    )}
                  </span>
                )}
              </div>
              {fieldErrors.confirmPassword && (
                <p className="text-xs text-destructive">{fieldErrors.confirmPassword}</p>
              )}
            </div>

            <Button type="submit" size="lg" className="mt-1 w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Creating your account…
                </>
              ) : (
                "Create account"
              )}
            </Button>
          </form>

          <p className="mt-8 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
