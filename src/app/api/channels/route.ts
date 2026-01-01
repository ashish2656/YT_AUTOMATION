import { NextResponse } from "next/server";
import { getDatabase } from "@/lib/mongodb";

export const dynamic = 'force-dynamic';

// GET - Get all channels configuration
export async function GET() {
  try {
    const db = await getDatabase();
    const channels = db.collection('channels');
    
    const channelDocs = await channels.find({}).toArray();
    
    return NextResponse.json({
      success: true,
      channels: channelDocs.map(ch => ({
        id: ch.channel_id,
        name: ch.channel_name,
        drive_folder_id: ch.drive_folder_id || ch.drive_folder_url,
        youtube_account: ch.channel_id,
        enabled: ch.enabled ?? true,
        categories: ch.categories || [],
        templates: {
          title: ch.title_template || '{trending_title}',
          description: ch.description_template || '{trending_description}'
        },
        uploaded_count: ch.uploaded_count || 0
      }))
    });
  } catch (error) {
    console.error("Failed to get channels:", error);
    return NextResponse.json(
      { success: false, error: "Failed to get channels" },
      { status: 500 }
    );
  }
}

// POST - Update channel configuration
export async function POST(request: Request) {
  try {
    const db = await getDatabase();
    const channels = db.collection('channels');
    
    const body = await request.json();
    const { action, channelId, channelData } = body;
    
    if (action === "update") {
      await channels.updateOne(
        { channel_id: channelId },
        { $set: channelData }
      );
    } else if (action === "create") {
      await channels.insertOne({
        ...channelData,
        created_at: new Date().toISOString()
      });
    } else if (action === "delete") {
      await channels.deleteOne({ channel_id: channelId });
    } else if (action === "toggle") {
      const channel = await channels.findOne({ channel_id: channelId });
      if (channel) {
        await channels.updateOne(
          { channel_id: channelId },
          { $set: { enabled: !channel.enabled } }
        );
      }
    } else {
      return NextResponse.json(
        { success: false, error: "Invalid action" },
        { status: 400 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to update channels:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update channels" },
      { status: 500 }
    );
  }
}
