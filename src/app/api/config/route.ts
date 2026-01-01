import { NextResponse } from "next/server";
import { getDatabase } from "@/lib/mongodb";

export const dynamic = 'force-dynamic';

// GET current config
export async function GET() {
  try {
    const db = await getDatabase();
    const config = db.collection('config');
    
    const configDoc = await config.findOne({ _id: 'main' as unknown as import('mongodb').ObjectId });
    
    return NextResponse.json({
      success: true,
      config: configDoc || {
        upload_schedule: "8AM, 1PM, 8PM IST (via GitHub Actions)",
        note: "Configuration managed via GitHub repository"
      }
    });
  } catch (error) {
    console.error("Failed to get config:", error);
    return NextResponse.json(
      { success: false, error: "Failed to get config" },
      { status: 500 }
    );
  }
}

// POST to update config
export async function POST(request: Request) {
  try {
    const db = await getDatabase();
    const config = db.collection('config');
    
    const body = await request.json();
    const { field, value } = body;

    await config.updateOne(
      { _id: 'main' as unknown as import('mongodb').ObjectId },
      { $set: { [field]: value } },
      { upsert: true }
    );

    return NextResponse.json({
      success: true,
      message: `Updated ${field} successfully`
    });
  } catch (error) {
    console.error("Failed to update config:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update config" },
      { status: 500 }
    );
  }
}
