import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET() {
  const res = await fetch(`${INTERNAL}/subscriptions`, { cache: "no-store" });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function POST(req: NextRequest) {
  const body = await req.text();
  const res = await fetch(`${INTERNAL}/subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
