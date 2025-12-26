import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);
const PYTHON_DIR = path.join(process.cwd(), "python");
const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";

// This endpoint is called by a cron job to auto-upload
export async function GET(request: Request) {
  // Verify cron secret to prevent unauthorized access
  const authHeader = request.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;
  
  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json(
      { success: false, error: "Unauthorized" },
      { status: 401 }
    );
  }

  try {
    const scriptPath = path.join(PYTHON_DIR, "automation.py");
    const { stdout, stderr } = await execAsync(
      `"${PYTHON_BIN}" "${scriptPath}" upload`
    );

    console.log("Cron upload output:", stdout);
    
    if (stderr) {
      console.error("Cron upload stderr:", stderr);
    }

    const result = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: result.success,
      message: result.success ? `Uploaded: ${result.fileName}` : result.error,
      videoId: result.videoId,
      fileName: result.fileName,
      youtubeUrl: result.youtubeUrl,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("Cron upload failed:", error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : "Upload failed",
        timestamp: new Date().toISOString()
      },
      { status: 500 }
    );
  }
}
