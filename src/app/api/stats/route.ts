import { NextResponse } from "next/server";
import { getDatabase } from "@/lib/mongodb";

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const db = await getDatabase();
    const history = db.collection('upload_history');
    const channels = db.collection('channels');
    
    // Get all channels
    const channelDocs = await channels.find({}).toArray();
    
    // Get uploaded count from history
    const uploadedCount = await history.countDocuments({});
    
    // Get uploads per channel
    const uploadsByChannel: Record<string, number> = {};
    for (const channel of channelDocs) {
      const count = await history.countDocuments({ channel_id: channel.channel_id });
      uploadsByChannel[channel.channel_id] = count;
    }

    return NextResponse.json({
      success: true,
      stats: {
        total: "See GitHub Actions",
        uploaded: uploadedCount,
        pending: "See GitHub Actions",
        uploadsByChannel
      }
    });
  } catch (error) {
    console.error("Failed to get stats:", error);
    return NextResponse.json(
      { success: false, error: "Failed to get stats" },
      { status: 500 }
    );
  }
}
