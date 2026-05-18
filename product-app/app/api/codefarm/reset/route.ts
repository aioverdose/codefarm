import { codefarmJson, projectPayload } from "@/lib/codefarm";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const project = projectPayload(body.project ?? body);
    return Response.json(await codefarmJson("/api/reset", {
      method: "POST",
      body: JSON.stringify({
        project_id: body.project_id,
        recreate: body.recreate ?? true,
        project
      })
    }));
  } catch (error) {
    return Response.json({ ok: false, error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 });
  }
}
