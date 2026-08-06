/**
 * Generates a private workspace (Organization) name for a newly
 * registering user.
 *
 * The backend's /auth/register contract requires an organization_name:
 * it joins an existing organization of that exact name if one exists,
 * or creates a new one (making the registrant its admin) if not (see
 * AuthService.register() on the backend). Deriving this from the
 * user's email domain was considered and rejected -- most users
 * register with personal providers (Gmail, Outlook, Yahoo, ...), which
 * would incorrectly group unrelated strangers into the same
 * organization.
 *
 * Instead, every registration gets its own private workspace. The
 * short suffix guarantees name uniqueness (Organization.name has a
 * database-level unique constraint) -- without it, two users who
 * happen to share a first name (e.g. two people named "Jane") would
 * collide, and the second "Jane" would silently join the first Jane's
 * real organization as a member instead of getting her own isolated
 * workspace. This directly defeats the "each user has an isolated
 * workspace" guarantee this feature exists for, so the collision has
 * to be prevented up front, not detected after the fact -- by the
 * time a collision could be observed, the user's email is already
 * registered and the operation can't be retried under a different name.
 */
export function generateWorkspaceName(fullName: string): string {
  const firstName = fullName.trim().split(/\s+/)[0];
  const suffix = generateSuffix();
  return firstName ? `${firstName}'s Workspace (${suffix})` : `My Workspace (${suffix})`;
}

function generateSuffix(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID().replace(/-/g, "").slice(0, 6).toUpperCase();
  }
  return Math.random().toString(36).slice(2, 8).toUpperCase();
}
