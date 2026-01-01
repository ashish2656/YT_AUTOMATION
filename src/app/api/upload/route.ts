import { NextResponse } from "next/server";

export const dynamic = 'force-dynamic';

// Uploads are handled by GitHub Actions on schedule
// Manual uploads not available on Vercel (no Python)
export async function POST() {
  return NextResponse.json({
    success: false,
    error: "Manual uploads are not available on Vercel. Uploads run automatically via GitHub Actions at 8AM, 1PM, and 8PM IST. You can also trigger manually from GitHub Actions tab."
  }, { status: 400 });
}
