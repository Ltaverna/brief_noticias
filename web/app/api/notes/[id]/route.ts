import { NextResponse } from "next/server";
const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function DELETE(
  _req: Request, { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const r = await fetch(`${INTERNAL}/notes/${id}`, { method: "DELETE" });
  return new NextResponse(null, { status: r.status });
}
