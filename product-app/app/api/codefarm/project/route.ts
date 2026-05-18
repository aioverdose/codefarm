import { codefarmJson, projectPayload } from "@/lib/codefarm";
export async function POST(request: Request) {
  try {
    const payload = projectPayload(await request.json());
    return Response.json(await codefarmJson("/api/project", { method: "POST", body: JSON.stringify(payload) }));
  } catch (error) {
    return Response.json({ ok: false, error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 });
  }
}