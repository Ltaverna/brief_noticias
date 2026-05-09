import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const res = await fetch(`${INTERNAL}/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    cache: "no-store",
  });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

// Long timeout for the GPT-4o synthesis (~5-15s typical)
export const maxDuration = 60;
