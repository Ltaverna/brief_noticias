import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  const qs = req.nextUrl.search;
  const res = await fetch(`${INTERNAL}/clusters/${id}/by-author${qs}`, {
    cache: "no-store",
  });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
