import { codefarmJson } from "@/lib/codefarm";
export async function POST() {
  try { return Response.json(await codefarmJson("/api/run-once", { method: "POST" })); }
  catch (error) { return Response.json({ ok: false, error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 }); }
}