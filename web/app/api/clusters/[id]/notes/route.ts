import { NextRequest, NextResponse } from "next/server";
const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET(
  _req: Request, { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const r = await fetch(`${INTERNAL}/clusters/${id}/notes`, { cache: "no-store" });
  return new NextResponse(await r.text(), {
    status: r.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function POST(
  req: NextRequest, { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await req.text();
  const r = await fetch(`${INTERNAL}/clusters/${id}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return new NextResponse(await r.text(), {
    status: r.status,
    headers: { "Content-Type": "application/json" },
  });
}
