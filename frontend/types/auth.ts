export interface RoleRead {
  id: string;
  name:
    | "super_admin"
    | "organization_admin"
    | "copilot_creator"
    | "knowledge_manager"
    | "end_user";
  description: string | null;
}

export interface OrganizationRead {
  id: string;
  name: string;
  created_at: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  organization_id: string;
  role: RoleRead;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
  organization_name: string;
}
