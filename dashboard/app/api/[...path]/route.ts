/**
 * Proxies browser calls to the runtime API.
 *
 * Keeping them same-origin means the deployment needs no CORS rules and no public
 * URL for the API: only this server has to know where the runtime is.
 */
const RUNTIME = process.env.VOCALIS_API_URL ?? "http://localhost:8000";

async function proxy(request: Request, path: string[]): Promise<Response> {
  const url = new URL(`${RUNTIME}/${path.join("/")}`);
  url.search = new URL(request.url).search;

  const response = await fetch(url, {
    method: request.method,
    headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
    cache: "no-store",
  }).catch(() => null);

  if (!response) {
    return Response.json(
      { detail: `the Vocalis runtime isn't reachable at ${RUNTIME}` },
      { status: 502 },
    );
  }

  return new Response(response.body, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  });
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, { params }: Context) {
  return proxy(request, (await params).path);
}
export async function POST(request: Request, { params }: Context) {
  return proxy(request, (await params).path);
}
export async function PUT(request: Request, { params }: Context) {
  return proxy(request, (await params).path);
}
export async function DELETE(request: Request, { params }: Context) {
  return proxy(request, (await params).path);
}
