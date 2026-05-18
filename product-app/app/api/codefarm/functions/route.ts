import { exposedFunctionCatalog } from "@/lib/codefarm";
export async function GET(request: Request) {
  const token = request.headers.get("x-functions-token");
  if (!process.env.CODEFARM_FUNCTIONS_TOKEN || token !== process.env.CODEFARM_FUNCTIONS_TOKEN) {
    return Response.json({ ok: false, error: "Not found" }, { status: 404 });
  }
  return Response.json({ ok: true, functions: exposedFunctionCatalog });
}