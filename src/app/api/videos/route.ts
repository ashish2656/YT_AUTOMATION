import { NextResponse } from "next/server";

export const dynamic = 'force-dynamic';

// Videos are fetched from Google Drive - only works during GitHub Actions upload
// Dashboard shows upload history instead
export async function GET() {
  return NextResponse.json({
    success: true,
    videos: [],
    message: "Video list is fetched during GitHub Actions upload. View upload history instead."
  });
}
