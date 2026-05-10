import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET(req: NextRequest) {
  const conversationId = req.nextUrl.searchParams.get("conversation_id");
  if (!conversationId) {
    return NextResponse.json([], { status: 200 });
  }
  const res = await fetch(
    `${INTERNAL}/qa/history?conversation_id=${encodeURIComponent(conversationId)}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    return NextResponse.json([], { status: 200 });
  }
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
