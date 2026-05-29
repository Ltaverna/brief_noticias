import { NextRequest, NextResponse } from "next/server";

const INTERNAL = process.env.INTERNAL_API_URL ?? "http://api:8000";

async function proxy(req: NextRequest, segments: string[]) {
  const qs = req.nextUrl.search;
  const upstream = `${INTERNAL}/authors/${segments.join("/")}${qs}`;
  const init: RequestInit = {
    method: req.method,
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  const res = await fetch(upstream, init);
  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
