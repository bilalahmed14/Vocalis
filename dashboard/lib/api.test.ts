/**
 * The API client: how it addresses the runtime and how it reports refusals.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, apiReachable } from "@/lib/api";

function respond(body: unknown, status = 200) {
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(async () =>
    status === 204
      ? new Response(null, { status })
      : new Response(JSON.stringify(body), {
          status,
          headers: { "content-type": "application/json" },
        }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("calls the runtime directly on the server", async () => {
    const fetchMock = respond([]);

    await api.agents();

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/agents");
  });

  it("sends the config when saving a new version", async () => {
    const fetchMock = respond({ slug: "bot", version: 2 });
    const config = { schema_version: 1, name: "Bot", nodes: [], edges: [] };

    await api.save("bot", config as never, "tweak");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/agents/bot");
    expect(init).toMatchObject({ method: "PUT" });
    expect(JSON.parse(String(init?.body))).toEqual({ config, note: "tweak" });
  });

  it("turns a refused save into an ApiError carrying the node issues", async () => {
    respond(
      {
        detail: {
          issues: [
            { message: 'node "tts": unknown tts provider "elevenlab"', node_id: "tts", path: "" },
          ],
        },
      },
      422,
    );

    const error = await api.create({} as never).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.message).toBe('node "tts": unknown tts provider "elevenlab"');
    expect(error.issues[0].node_id).toBe("tts");
  });

  it("reports a plain detail string", async () => {
    respond({ detail: 'no agent called "nope"' }, 404);

    const error = await api.agent("nope").catch((e) => e);

    expect(error.message).toBe('no agent called "nope"');
  });

  it("handles an empty response", async () => {
    respond(null, 204);

    await expect(api.remove("bot")).resolves.toBeUndefined();
  });

  it("reports the runtime as down when it can't be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("fetch failed");
      }),
    );

    await expect(apiReachable()).resolves.toBe(false);
  });
});
