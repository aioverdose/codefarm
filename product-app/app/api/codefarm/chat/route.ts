import { codefarmJson } from "@/lib/codefarm";

export async function GET() {
  try {
    return Response.json(await codefarmJson("/api/chat"));
  } catch (error) {
    return Response.json({ ok: false, error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    return Response.json(await codefarmJson("/api/chat", { method: "POST", body: JSON.stringify(body) }));
  } catch (error) {
    return Response.json({ ok: false, error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 });
  }
}
