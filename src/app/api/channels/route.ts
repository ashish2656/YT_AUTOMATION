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
      // Map frontend format to database format
      const updateData: Record<string, unknown> = {};
      if (channelData.name) updateData.channel_name = channelData.name;
      if (channelData.drive_folder_id) {
        updateData.drive_folder_url = channelData.drive_folder_id;
        // Extract folder ID from URL
        if (channelData.drive_folder_id.includes('/folders/')) {
          updateData.drive_folder_id = channelData.drive_folder_id.split('/folders/')[1].split('?')[0].split('/')[0];
        } else {
          updateData.drive_folder_id = channelData.drive_folder_id;
        }
      }
      if (channelData.youtube_account) updateData.channel_id = channelData.youtube_account;
      if (channelData.enabled !== undefined) updateData.enabled = channelData.enabled;
      if (channelData.categories) updateData.categories = channelData.categories;
      if (channelData.templates) {
        updateData.title_template = channelData.templates.title;
        updateData.description_template = channelData.templates.description;
      }
      
      await channels.updateOne(
        { channel_id: channelId },
        { $set: updateData }
      );
    } else if (action === "create") {
      // Map frontend format to database format for new channel
      const newChannelId = channelData.youtube_account || `channel_${Date.now()}`;
      let driveFolderId = channelData.drive_folder_id || '';
      if (driveFolderId.includes('/folders/')) {
        driveFolderId = driveFolderId.split('/folders/')[1].split('?')[0].split('/')[0];
      }
      
      await channels.insertOne({
        channel_id: newChannelId,
        channel_name: channelData.name || '',
        drive_folder_url: channelData.drive_folder_id || '',
        drive_folder_id: driveFolderId,
        enabled: channelData.enabled ?? true,
        categories: channelData.categories || [],
        title_template: channelData.templates?.title || '{trending_title}',
        description_template: channelData.templates?.description || '{trending_description}',
        tags: ['shorts'],
        category_id: '22',
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
