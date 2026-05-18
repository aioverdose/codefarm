import { codefarmJson } from "@/lib/codefarm";
export async function GET() {
  try { return Response.json(await codefarmJson("/api/state")); }
  catch (error) { return Response.json({ ok: false, error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 }); }
}