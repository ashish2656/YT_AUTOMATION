import { NextResponse } from "next/server";
import { getDatabase } from "@/lib/mongodb";

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get("limit") || "50");
    const channelId = searchParams.get("channelId");
    
    const db = await getDatabase();
    const history = db.collection('upload_history');
    
    const query = channelId ? { channel_id: channelId } : {};
    
    const uploads = await history
      .find(query)
      .sort({ uploaded_at: -1 })
      .limit(limit)
      .toArray();
    
    return NextResponse.json({
      success: true,
      history: uploads.map(u => ({
        video_id: u.video_id,
        youtube_id: u.youtube_id,
        title: u.title,
        channel_id: u.channel_id,
        channel_name: u.channel_name,
        uploaded_at: u.uploaded_at,
        youtube_url: u.youtube_url
      }))
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to get history" },
      { status: 500 }
    );
  }
}
