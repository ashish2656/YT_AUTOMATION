import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export const dynamic = 'force-dynamic';

// GET - Get all available YouTube accounts from channels_config.json
export async function GET() {
  try {
    const configPath = path.join(process.cwd(), "python", "channels_config.json");
    
    if (!fs.existsSync(configPath)) {
      return NextResponse.json({
        success: false,
        error: "channels_config.json not found"
      }, { status: 404 });
    }
    
    const configData = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    const youtubeAccounts = configData.youtube_accounts || {};
    
    // Convert to array format for frontend
    const accounts = Object.entries(youtubeAccounts).map(([id, account]: [string, unknown]) => {
      const acc = account as { name?: string; token_env_var?: string };
      return {
        id,
        name: acc.name || id,
        token_env_var: acc.token_env_var || `GOOGLE_TOKEN_${id.toUpperCase()}_JSON`
      };
    });
    
    return NextResponse.json({
      success: true,
      accounts
    });
  } catch (error) {
    console.error("Failed to get accounts:", error);
    return NextResponse.json(
      { success: false, error: "Failed to get accounts" },
      { status: 500 }
    );
  }
}
