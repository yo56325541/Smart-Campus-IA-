import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createAdmissionCondition,
  createProgram,
  createTariff,
  deactivateProgram,
  deleteAdmissionCondition,
  deleteTariff,
  getAdmissionConditions,
  getPrograms,
  getProgram,
  getTariffs,
  updateAdmissionCondition,
  updateProgram,
  updateTariff,
} from "./programs";

describe("public program API", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends catalogue search and filters using backend query parameters", async () => {
    fetchMock.mockResolvedValue(new Response("[]", { status: 200 }));

    await getPrograms({
      institution: "IIT",
      level: "licence",
      q: "informatique",
      limit: 25,
      offset: 24,
    });

    const [request, options] = fetchMock.mock.calls[0];
    const url = new URL(String(request));
    expect(url.pathname).toBe("/programs");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      institution: "IIT",
      level: "licence",
      q: "informatique",
      limit: "25",
      offset: "24",
    });
    expect(options?.method).toBe("GET");
    expect(options?.cache).toBe("no-store");
    expect(options?.body).toBeUndefined();
    expect(new Headers(options?.headers).get("Authorization")).toBeNull();
  });

  it("uses the detail and dedicated information routes with encoded slugs", async () => {
    fetchMock.mockImplementation(
      async () => new Response("{}", { status: 200 }),
    );

    await getProgram("genie logiciel");
    await getAdmissionConditions("genie logiciel");
    await getTariffs("genie logiciel");

    expect(
      fetchMock.mock.calls.map(([request]) => new URL(String(request)).pathname),
    ).toEqual([
      "/programs/genie%20logiciel",
      "/programs/genie%20logiciel/admission-conditions",
      "/programs/genie%20logiciel/tariffs",
    ]);
  });

  it("surfaces API failures with their HTTP status", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 503 }));

    await expect(getPrograms()).rejects.toMatchObject({
      name: "ProgramApiError",
      status: 503,
    });
  });

  it("requests inactive programs with an administrator bearer token", async () => {
    fetchMock.mockResolvedValue(new Response("[]", { status: 200 }));

    await getPrograms({ include_inactive: true, limit: 200 }, "admin-token");

    const [request, options] = fetchMock.mock.calls[0];
    const url = new URL(String(request));
    expect(url.pathname).toBe("/programs");
    expect(url.searchParams.get("include_inactive")).toBe("true");
    expect(url.searchParams.get("limit")).toBe("200");
    expect(new Headers(options?.headers).get("Authorization")).toBe(
      "Bearer admin-token",
    );
  });

  it("uses the admin program, condition and tariff mutation routes", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response("{}", { status: 201 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response("{}", { status: 201 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response("{}", { status: 201 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await createProgram(
      {
        slug: "genie-logiciel",
        institution: "IIT",
        level: "ingenierie",
        name: "Génie logiciel",
      },
      "admin-token",
    );
    await updateProgram("genie-logiciel", { name: "Génie logiciel" }, "admin-token");
    await deactivateProgram("genie-logiciel", "admin-token");
    await createAdmissionCondition(
      "genie-logiciel",
      { title: "Diplôme requis" },
      "admin-token",
    );
    await updateAdmissionCondition("condition-id", { position: 2 }, "admin-token");
    await deleteAdmissionCondition("condition-id", "admin-token");
    await createTariff(
      "genie-logiciel",
      { academic_year: "2026-2027", amount: "1200.00" },
      "admin-token",
    );
    await updateTariff("tariff-id", { amount: "1250.00" }, "admin-token");
    await deleteTariff("tariff-id", "admin-token");

    const calls = fetchMock.mock.calls;
    expect(calls.map(([url, options]) => [
      new URL(String(url)).pathname,
      options?.method ?? "GET",
    ])).toEqual([
      ["/programs", "POST"],
      ["/programs/genie-logiciel", "PATCH"],
      ["/programs/genie-logiciel", "DELETE"],
      ["/programs/genie-logiciel/admission-conditions", "POST"],
      ["/admission-conditions/condition-id", "PATCH"],
      ["/admission-conditions/condition-id", "DELETE"],
      ["/programs/genie-logiciel/tariffs", "POST"],
      ["/tariffs/tariff-id", "PATCH"],
      ["/tariffs/tariff-id", "DELETE"],
    ]);

    for (const [, options] of calls) {
      expect(new Headers(options?.headers).get("Authorization")).toBe(
        "Bearer admin-token",
      );
    }

    expect(calls[3][1]?.body).toBe(JSON.stringify({ title: "Diplôme requis" }));
    expect(calls[6][1]?.body).toBe(
      JSON.stringify({ academic_year: "2026-2027", amount: "1200.00" }),
    );
  });
});
