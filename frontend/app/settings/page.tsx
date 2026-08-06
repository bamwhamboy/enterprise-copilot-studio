"use client";

import { useQuery } from "@tanstack/react-query";
import { Settings, Building2, UserRound, Cpu, Mail, Calendar, ShieldCheck } from "lucide-react";

import { useAuthStore } from "@/store/auth-store";
import { organizationsApi } from "@/lib/api/organizations";
import { copilotsApi } from "@/lib/api/copilots";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";

function getInitials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  const { data: organizations, isLoading: orgLoading } = useQuery({
    queryKey: ["organizations"],
    queryFn: organizationsApi.list,
    // An organization's own name/id essentially never changes mid-session
    // -- no reason to re-verify this as eagerly as the default 60s.
    staleTime: 10 * 60 * 1000,
  });

  const { data: copilots, isLoading: copilotsLoading } = useQuery({
    queryKey: ["copilots"],
    queryFn: copilotsApi.list,
  });

  const organization = organizations?.find((o) => o.id === user?.organization_id) ?? organizations?.[0];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Settings"
        description="Your profile, organization, and copilot model configuration."
        icon={Settings}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Profile */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserRound className="size-4 text-primary" />
              Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {!user ? (
              <div className="flex items-center gap-3">
                <Skeleton className="size-12 rounded-full" />
                <div className="flex flex-1 flex-col gap-1.5">
                  <Skeleton className="h-4 w-1/2 rounded-md" />
                  <Skeleton className="h-3 w-1/3 rounded-md" />
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3">
                  <Avatar className="size-12">
                    <AvatarFallback className="bg-primary/10 text-base text-primary">
                      {getInitials(user.full_name || user.email)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {user.full_name || "—"}
                    </p>
                    <Badge variant="secondary" className="mt-1 capitalize">
                      {user.role.name.replace(/_/g, " ")}
                    </Badge>
                  </div>
                </div>
                <dl className="flex flex-col gap-2.5 text-sm">
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center gap-1.5 text-muted-foreground">
                      <Mail className="size-3.5" />
                      Email
                    </dt>
                    <dd className="font-medium text-foreground">{user.email}</dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center gap-1.5 text-muted-foreground">
                      <ShieldCheck className="size-3.5" />
                      Status
                    </dt>
                    <dd>
                      <Badge variant={user.is_active ? "success" : "destructive"}>
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </dd>
                  </div>
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center gap-1.5 text-muted-foreground">
                      <Calendar className="size-3.5" />
                      Member since
                    </dt>
                    <dd className="font-medium text-foreground">
                      {formatDate(user.created_at)}
                    </dd>
                  </div>
                </dl>
              </>
            )}
          </CardContent>
        </Card>

        {/* Organization */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="size-4 text-primary" />
              Organization
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {orgLoading ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-5 w-1/2 rounded-md" />
                <Skeleton className="h-3 w-1/3 rounded-md" />
              </div>
            ) : organization ? (
              <dl className="flex flex-col gap-2.5 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Name</dt>
                  <dd className="font-medium text-foreground">{organization.name}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Organization ID</dt>
                  <dd className="max-w-[60%] truncate font-mono text-xs text-foreground">
                    {organization.id}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-1.5 text-muted-foreground">
                    <Calendar className="size-3.5" />
                    Created
                  </dt>
                  <dd className="font-medium text-foreground">
                    {formatDate(organization.created_at)}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">No organization found.</p>
            )}
          </CardContent>
        </Card>

        {/* Copilot model configuration */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Cpu className="size-4 text-primary" />
              Copilot Model Configuration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-4 text-xs text-muted-foreground">
              Each copilot has its own model — change it from the Copilot Management page.
            </p>
            {copilotsLoading ? (
              <div className="flex flex-col gap-2">
                {[0, 1].map((i) => (
                  <Skeleton key={i} className="h-10 w-full rounded-md" />
                ))}
              </div>
            ) : copilots && copilots.length > 0 ? (
              <div className="flex flex-col divide-y divide-border">
                {copilots.map((copilot) => (
                  <div key={copilot.id} className="flex items-center justify-between py-2.5">
                    <span className="text-sm font-medium text-foreground">{copilot.name}</span>
                    <Badge variant="outline" className="font-mono text-[11px]">
                      {copilot.model}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No copilots yet — create one from Copilot Management.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
