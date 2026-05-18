import { codefarmBinary } from "@/lib/codefarm";
export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const projectId = url.searchParams.get("project_id") || "";
    if (!/^[a-z0-9-]{1,64}$/.test(projectId)) return Response.json({ ok: false, error: "Invalid project id" }, { status: 400 });
    const upstream = await codefarmBinary(`/api/export?project_id=${projectId}`);
    const body = await upstream.arrayBuffer();
    return new Response(body, { headers: { "Content-Type": "application/zip", "Content-Disposition": upstream.headers.get("Content-Disposition") || `attachment; filename="${projectId}.zip"` } });
  } catch (error) {
    return Response.json({ ok: false, error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 });
  }
}