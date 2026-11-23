import type {
  ConditionIn,
  ConditionOut,
  ConditionUpdate,
  Institution,
  ProgramDetail,
  ProgramIn,
  ProgramOut,
  ProgramUpdate,
  TariffIn,
  TariffOut,
  TariffUpdate,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ProgramApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ProgramApiError";
  }
}

interface ProgramRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  accessToken?: string;
  body?: unknown;
}

async function request<T>(
  path: string,
  options: ProgramRequestOptions = {},
): Promise<T> {
  const url = new URL(path, API_BASE_URL);
  const headers = new Headers();
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  if (options.accessToken) {
    headers.set("Authorization", `Bearer ${options.accessToken}`);
  }
  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  if (!response.ok) {
    const responseText = await response.text();
    let detail = `L’API SmartCampus a répondu avec le statut ${response.status}.`;
    if (responseText) {
      try {
        const result = JSON.parse(responseText) as { detail?: unknown };
        if (typeof result.detail === "string") detail = result.detail;
      } catch {
        detail = responseText;
      }
    }
    throw new ProgramApiError(
      detail,
      response.status,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface ProgramSearch {
  institution?: Institution;
  level?: string;
  q?: string;
  include_inactive?: boolean;
  limit?: number;
  offset?: number;
}

export function getPrograms(
  filters: ProgramSearch = {},
  accessToken?: string,
) {
  const params = new URLSearchParams();
  if (filters.institution) params.set("institution", filters.institution);
  if (filters.level) params.set("level", filters.level);
  if (filters.q) params.set("q", filters.q);
  if (filters.include_inactive) params.set("include_inactive", "true");
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));

  const query = params.size > 0 ? `?${params.toString()}` : "";
  return request<ProgramOut[]>(`/programs${query}`, { accessToken });
}

export function getProgram(slug: string, accessToken?: string) {
  return request<ProgramDetail>(`/programs/${encodeURIComponent(slug)}`, {
    accessToken,
  });
}

export function getAdmissionConditions(slug: string, accessToken?: string) {
  return request<ConditionOut[]>(
    `/programs/${encodeURIComponent(slug)}/admission-conditions`,
    { accessToken },
  );
}

export function getTariffs(slug: string, accessToken?: string) {
  return request<TariffOut[]>(`/programs/${encodeURIComponent(slug)}/tariffs`, {
    accessToken,
  });
}

export function createProgram(body: ProgramIn, accessToken: string) {
  return request<ProgramOut>("/programs", {
    method: "POST",
    body,
    accessToken,
  });
}

export function updateProgram(
  slug: string,
  body: ProgramUpdate,
  accessToken: string,
) {
  return request<ProgramOut>(`/programs/${encodeURIComponent(slug)}`, {
    method: "PATCH",
    body,
    accessToken,
  });
}

export function deactivateProgram(slug: string, accessToken: string) {
  return request<void>(`/programs/${encodeURIComponent(slug)}`, {
    method: "DELETE",
    accessToken,
  });
}

export function createAdmissionCondition(
  slug: string,
  body: ConditionIn,
  accessToken: string,
) {
  return request<ConditionOut>(
    `/programs/${encodeURIComponent(slug)}/admission-conditions`,
    { method: "POST", body, accessToken },
  );
}

export function updateAdmissionCondition(
  conditionId: string,
  body: ConditionUpdate,
  accessToken: string,
) {
  return request<ConditionOut>(
    `/admission-conditions/${encodeURIComponent(conditionId)}`,
    { method: "PATCH", body, accessToken },
  );
}

export function deleteAdmissionCondition(
  conditionId: string,
  accessToken: string,
) {
  return request<void>(
    `/admission-conditions/${encodeURIComponent(conditionId)}`,
    { method: "DELETE", accessToken },
  );
}

export function createTariff(
  slug: string,
  body: TariffIn,
  accessToken: string,
) {
  return request<TariffOut>(`/programs/${encodeURIComponent(slug)}/tariffs`, {
    method: "POST",
    body,
    accessToken,
  });
}

export function updateTariff(
  tariffId: string,
  body: TariffUpdate,
  accessToken: string,
) {
  return request<TariffOut>(`/tariffs/${encodeURIComponent(tariffId)}`, {
    method: "PATCH",
    body,
    accessToken,
  });
}

export function deleteTariff(tariffId: string, accessToken: string) {
  return request<void>(`/tariffs/${encodeURIComponent(tariffId)}`, {
    method: "DELETE",
    accessToken,
  });
}
