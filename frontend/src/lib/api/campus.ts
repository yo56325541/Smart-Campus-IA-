import type {
  AdminCreateUserIn,
  ApplicationDetail,
  ApplicationIn,
  ApplicationOut,
  ApplicationStatus,
  ApplicationStatusIn,
  ConversationIn,
  ConversationOut,
  LinkOut,
  LoginIn,
  RegisterIn,
  SessionInfo,
  SessionOut,
  TokenOut,
  UserActiveIn,
  UserOut,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class CampusApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "CampusApiError";
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  sessionToken?: string;
  accessToken?: string;
}

async function request<T>(path: string, options: RequestOptions = {}) {
  const headers = new Headers();
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.sessionToken) {
    headers.set("X-Session-Token", options.sessionToken);
  }
  if (options.accessToken) {
    headers.set("Authorization", `Bearer ${options.accessToken}`);
  }

  const response = await fetch(new URL(path, API_BASE_URL), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  if (!response.ok) {
    const result = (await response.json()) as { detail?: unknown };
    const detail =
      typeof result.detail === "string"
        ? result.detail
        : "Vérifiez les informations saisies puis réessayez.";
    throw new CampusApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function createVisitorSession() {
  return request<SessionOut>("/sessions", { method: "POST" });
}

export function getVisitorSession(sessionToken: string) {
  return request<SessionInfo>("/sessions/me", { sessionToken });
}

export function linkVisitorSession(
  sessionToken: string,
  accessToken: string,
) {
  return request<LinkOut>("/sessions/link", {
    method: "POST",
    sessionToken,
    accessToken,
  });
}

export function createConversation(
  title: ConversationIn["title"],
  sessionToken: string,
  accessToken?: string,
) {
  return request<ConversationOut>("/conversations", {
    method: "POST",
    body: { title } satisfies ConversationIn,
    sessionToken,
    accessToken,
  });
}

export function getConversations(
  sessionToken: string | undefined,
  accessToken?: string,
  offset = 0,
  limit = 50,
) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request<ConversationOut[]>(`/conversations?${params}`, {
    sessionToken,
    accessToken,
  });
}

export function getConversation(
  conversationId: string,
  sessionToken: string | undefined,
  accessToken?: string,
) {
  return request<ConversationOut>(
    `/conversations/${encodeURIComponent(conversationId)}`,
    { sessionToken, accessToken },
  );
}

export function registerCandidate(body: RegisterIn, sessionToken: string) {
  return request<TokenOut>("/auth/register", {
    method: "POST",
    body,
    sessionToken,
  });
}

export function loginUser(body: LoginIn) {
  return request<TokenOut>("/auth/login", {
    method: "POST",
    body,
  });
}

export function getCurrentUser(accessToken: string) {
  return request<UserOut>("/auth/me", { accessToken });
}

export function getMyApplications(
  accessToken: string,
  offset = 0,
  limit = 200,
) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request<ApplicationOut[]>(`/applications/me?${params}`, {
    accessToken,
  });
}

export function createApplication(body: ApplicationIn, accessToken: string) {
  return request<ApplicationOut>("/applications", {
    method: "POST",
    body,
    accessToken,
  });
}

export function getMyApplication(
  applicationId: string,
  accessToken: string,
) {
  return request<ApplicationOut>(
    `/applications/${encodeURIComponent(applicationId)}`,
    { accessToken },
  );
}

export function withdrawApplication(
  applicationId: string,
  accessToken: string,
) {
  return request<void>(
    `/applications/${encodeURIComponent(applicationId)}`,
    { method: "DELETE", accessToken },
  );
}

export function getAdminUsers(accessToken: string, offset = 0, limit = 200) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request<UserOut[]>(`/admin/users?${params}`, { accessToken });
}

export function createAdminUser(
  body: AdminCreateUserIn,
  accessToken: string,
) {
  return request<UserOut>("/admin/users", {
    method: "POST",
    body,
    accessToken,
  });
}

export function setAdminUserActive(
  userId: string,
  body: UserActiveIn,
  accessToken: string,
) {
  return request<UserOut>(`/admin/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body,
    accessToken,
  });
}

export function getAdminApplications(
  accessToken: string,
  filters: {
    status?: ApplicationStatus;
    limit?: number;
    offset?: number;
  } = {},
) {
  const params = new URLSearchParams({
    limit: String(filters.limit ?? 200),
    offset: String(filters.offset ?? 0),
  });
  if (filters.status) params.set("status", filters.status);
  return request<ApplicationDetail[]>(`/admin/applications?${params}`, {
    accessToken,
  });
}

export function getAdminApplication(
  applicationId: string,
  accessToken: string,
) {
  return request<ApplicationDetail>(
    `/admin/applications/${encodeURIComponent(applicationId)}`,
    { accessToken },
  );
}

export function updateAdminApplicationStatus(
  applicationId: string,
  body: ApplicationStatusIn,
  accessToken: string,
) {
  return request<ApplicationOut>(
    `/admin/applications/${encodeURIComponent(applicationId)}/status`,
    { method: "PATCH", body, accessToken },
  );
}

export function deleteAdminApplication(
  applicationId: string,
  accessToken: string,
) {
  return request<void>(
    `/admin/applications/${encodeURIComponent(applicationId)}`,
    { method: "DELETE", accessToken },
  );
}
