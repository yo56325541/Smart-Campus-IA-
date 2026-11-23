import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createApplication,
  createConversation,
  createVisitorSession,
  getConversation,
  getConversations,
  getCurrentUser,
  getAdminApplication,
  getAdminApplications,
  getAdminUsers,
  getMyApplication,
  getMyApplications,
  getVisitorSession,
  linkVisitorSession,
  loginUser,
  registerCandidate,
  createAdminUser,
  deleteAdminApplication,
  setAdminUserActive,
  updateAdminApplicationStatus,
  withdrawApplication,
} from "./campus";

describe("visitor, conversation and authentication API", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates an anonymous session without requiring prior credentials", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          session_token: "server-session-token",
          expires_at: "2026-11-24T12:00:00Z",
        }),
        { status: 201 },
      ),
    );

    await createVisitorSession();

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://127.0.0.1:8000/sessions");
    expect(options?.method).toBe("POST");
    expect(new Headers(options?.headers).get("X-Session-Token")).toBeNull();
  });

  it("sends both ownership credentials when retrieving conversations", async () => {
    fetchMock.mockImplementation(async () => new Response("[]", { status: 200 }));

    await getConversations("visitor-token", "candidate-token", 50, 25);
    await getConversation(
      "8d97f777-86ca-43df-ae23-0c8b761b7f5a",
      "visitor-token",
      "candidate-token",
    );

    const [listUrl, listOptions] = fetchMock.mock.calls[0];
    expect(String(listUrl)).toBe(
      "http://127.0.0.1:8000/conversations?limit=25&offset=50",
    );
    expect(new Headers(listOptions?.headers).get("X-Session-Token")).toBe(
      "visitor-token",
    );
    expect(new Headers(listOptions?.headers).get("Authorization")).toBe(
      "Bearer candidate-token",
    );

    const [detailUrl, detailOptions] = fetchMock.mock.calls[1];
    expect(String(detailUrl)).toBe(
      "http://127.0.0.1:8000/conversations/8d97f777-86ca-43df-ae23-0c8b761b7f5a",
    );
    expect(new Headers(detailOptions?.headers).get("X-Session-Token")).toBe(
      "visitor-token",
    );
  });

  it("uses only the candidate token when reading account-owned conversations", async () => {
    fetchMock.mockImplementation(async () => new Response("[]", { status: 200 }));

    await getConversations(undefined, "candidate-token");
    await getConversation(
      "8d97f777-86ca-43df-ae23-0c8b761b7f5a",
      undefined,
      "candidate-token",
    );

    for (const [, options] of fetchMock.mock.calls) {
      const headers = new Headers(options?.headers);
      expect(headers.get("X-Session-Token")).toBeNull();
      expect(headers.get("Authorization")).toBe("Bearer candidate-token");
    }
  });

  it("creates conversations with the backend title and session header", async () => {
    fetchMock.mockResolvedValue(new Response("{}", { status: 201 }));

    await createConversation(
      "Nouvelle conversation",
      "visitor-token",
      "candidate-token",
    );

    const [, options] = fetchMock.mock.calls[0];
    expect(options?.method).toBe("POST");
    expect(options?.body).toBe(
      JSON.stringify({ title: "Nouvelle conversation" }),
    );
    expect(new Headers(options?.headers).get("X-Session-Token")).toBe(
      "visitor-token",
    );
    expect(new Headers(options?.headers).get("Authorization")).toBe(
      "Bearer candidate-token",
    );
  });

  it("authenticates without attaching the visitor session before checking the role", async () => {
    fetchMock.mockImplementation(async () => new Response("{}", { status: 200 }));

    await loginUser({ email: "candidate@example.test", password: "passphrase" });
    await registerCandidate(
      {
        email: "new@example.test",
        password: "passphrase",
        full_name: "New Candidate",
      },
      "visitor-token",
    );
    await linkVisitorSession("visitor-token", "access");
    await getCurrentUser("access");
    await getVisitorSession("visitor-token");

    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/auth/login",
      "/auth/register",
      "/sessions/link",
      "/auth/me",
      "/sessions/me",
    ]);

    const [, loginOptions] = fetchMock.mock.calls[0];
    expect(loginOptions?.body).toBe(
      JSON.stringify({
        email: "candidate@example.test",
        password: "passphrase",
      }),
    );
    expect(new Headers(loginOptions?.headers).get("X-Session-Token")).toBeNull();

    const [, linkOptions] = fetchMock.mock.calls[2];
    expect(new Headers(linkOptions?.headers).get("X-Session-Token")).toBe(
      "visitor-token",
    );
    expect(new Headers(linkOptions?.headers).get("Authorization")).toBe(
      "Bearer access",
    );
    const [, profileOptions] = fetchMock.mock.calls[3];
    expect(new Headers(profileOptions?.headers).get("Authorization")).toBe(
      "Bearer access",
    );
  });

  it("surfaces backend errors with their status and detail", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Identifiants invalides" }), {
        status: 401,
      }),
    );

    await expect(
      loginUser({ email: "candidate@example.test", password: "wrong" }),
    ).rejects.toMatchObject({
      name: "CampusApiError",
      status: 401,
      message: "Identifiants invalides",
    });
  });

  it("uses the candidate-only application list and bearer token", async () => {
    fetchMock.mockResolvedValue(new Response("[]", { status: 200 }));

    await getMyApplications("candidate-token", 10, 25);

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(
      "http://127.0.0.1:8000/applications/me?limit=25&offset=10",
    );
    expect(options?.method).toBe("GET");
    expect(new Headers(options?.headers).get("Authorization")).toBe(
      "Bearer candidate-token",
    );
  });

  it("creates an application with the backend request shape", async () => {
    fetchMock.mockResolvedValue(new Response("{}", { status: 201 }));

    await createApplication(
      {
        program_id: "program-uuid",
        academic_year: "2026-2027",
        notes: "Dossier de candidature",
      },
      "candidate-token",
    );

    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://127.0.0.1:8000/applications");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBe(
      JSON.stringify({
        program_id: "program-uuid",
        academic_year: "2026-2027",
        notes: "Dossier de candidature",
      }),
    );
    expect(new Headers(options?.headers).get("Authorization")).toBe(
      "Bearer candidate-token",
    );
  });

  it("retrieves and withdraws a candidate-owned application", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    const applicationId = "8d97f777-86ca-43df-ae23-0c8b761b7f5a";
    await getMyApplication(applicationId, "candidate-token");
    await withdrawApplication(applicationId, "candidate-token");

    const [detailUrl, detailOptions] = fetchMock.mock.calls[0];
    expect(String(detailUrl)).toBe(
      `http://127.0.0.1:8000/applications/${applicationId}`,
    );
    expect(new Headers(detailOptions?.headers).get("Authorization")).toBe(
      "Bearer candidate-token",
    );

    const [deleteUrl, deleteOptions] = fetchMock.mock.calls[1];
    expect(String(deleteUrl)).toBe(
      `http://127.0.0.1:8000/applications/${applicationId}`,
    );
    expect(deleteOptions?.method).toBe("DELETE");
    expect(new Headers(deleteOptions?.headers).get("Authorization")).toBe(
      "Bearer candidate-token",
    );
  });

  it("uses the admin user routes with the exact request shapes and bearer token", async () => {
    fetchMock.mockImplementation(async () => new Response("[]", { status: 200 }));

    await getAdminUsers("admin-token", 10, 25);
    await createAdminUser(
      {
        email: "new-admin@example.test",
        password: "secure-password",
        full_name: "New Admin",
        role: "admin",
      },
      "admin-token",
    );
    await setAdminUserActive("user-uuid", { is_active: false }, "admin-token");

    const [listUrl, listOptions] = fetchMock.mock.calls[0];
    expect(String(listUrl)).toBe(
      "http://127.0.0.1:8000/admin/users?limit=25&offset=10",
    );
    expect(new Headers(listOptions?.headers).get("Authorization")).toBe(
      "Bearer admin-token",
    );

    const [, createOptions] = fetchMock.mock.calls[1];
    expect(createOptions?.method).toBe("POST");
    expect(createOptions?.body).toBe(
      JSON.stringify({
        email: "new-admin@example.test",
        password: "secure-password",
        full_name: "New Admin",
        role: "admin",
      }),
    );

    const [patchUrl, patchOptions] = fetchMock.mock.calls[2];
    expect(String(patchUrl)).toBe(
      "http://127.0.0.1:8000/admin/users/user-uuid",
    );
    expect(patchOptions?.method).toBe("PATCH");
    expect(patchOptions?.body).toBe(JSON.stringify({ is_active: false }));
    expect(new Headers(patchOptions?.headers).get("Authorization")).toBe(
      "Bearer admin-token",
    );
  });

  it("uses admin application routes, status filter and status update shape", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response("[]", { status: 200 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    const applicationId = "8d97f777-86ca-43df-ae23-0c8b761b7f5a";
    await getAdminApplications("admin-token", {
      status: "under_review",
      limit: 25,
      offset: 5,
    });
    await getAdminApplication(applicationId, "admin-token");
    await updateAdminApplicationStatus(
      applicationId,
      { status: "accepted" },
      "admin-token",
    );
    await deleteAdminApplication(applicationId, "admin-token");

    const [listUrl, listOptions] = fetchMock.mock.calls[0];
    expect(String(listUrl)).toBe(
      "http://127.0.0.1:8000/admin/applications?limit=25&offset=5&status=under_review",
    );
    expect(new Headers(listOptions?.headers).get("Authorization")).toBe(
      "Bearer admin-token",
    );

    const [detailUrl, detailOptions] = fetchMock.mock.calls[1];
    expect(String(detailUrl)).toBe(
      `http://127.0.0.1:8000/admin/applications/${applicationId}`,
    );
    expect(new Headers(detailOptions?.headers).get("Authorization")).toBe(
      "Bearer admin-token",
    );

    const [patchUrl, patchOptions] = fetchMock.mock.calls[2];
    expect(String(patchUrl)).toBe(
      `http://127.0.0.1:8000/admin/applications/${applicationId}/status`,
    );
    expect(patchOptions?.method).toBe("PATCH");
    expect(patchOptions?.body).toBe(JSON.stringify({ status: "accepted" }));

    const [deleteUrl, deleteOptions] = fetchMock.mock.calls[3];
    expect(String(deleteUrl)).toBe(
      `http://127.0.0.1:8000/admin/applications/${applicationId}`,
    );
    expect(deleteOptions?.method).toBe("DELETE");
  });
});
