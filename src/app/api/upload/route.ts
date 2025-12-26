import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);
const PYTHON_DIR = path.join(process.cwd(), "python");
const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";

export async function POST(request: Request) {
  try {
    // Check if a specific video ID was provided
    let videoFileId: string | null = null;
    try {
      const body = await request.json();
      videoFileId = body.videoId || null;
    } catch {
      // No body provided, upload next video
    }

    // Run the Python upload script
    const scriptPath = path.join(PYTHON_DIR, "automation.py");
    const command = videoFileId
      ? `"${PYTHON_BIN}" "${scriptPath}" upload "${videoFileId}"`
      : `"${PYTHON_BIN}" "${scriptPath}" upload`;

    const { stdout, stderr } = await execAsync(command);

    console.log("Upload output:", stdout);
    
    if (stderr) {
      console.error("Upload stderr:", stderr);
    }

    // Parse JSON response from Python
    const result = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: result.success,
      message: result.success ? "Video uploaded successfully!" : result.error,
      videoId: result.videoId,
      fileName: result.fileName,
      youtubeUrl: result.youtubeUrl
    });
  } catch (error) {
    console.error("Upload failed:", error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : "Upload failed" 
      },
      { status: 500 }
    );
  }
}
