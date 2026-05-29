import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.search;
  const res = await fetch(`${INTERNAL}/authors${qs}`, { cache: "no-store" });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
