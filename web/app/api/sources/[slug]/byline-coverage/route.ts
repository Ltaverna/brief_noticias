import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ slug: string }> },
) {
  const { slug } = await ctx.params;
  const res = await fetch(`${INTERNAL}/sources/${slug}/byline-coverage`, {
    cache: "no-store",
  });
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
