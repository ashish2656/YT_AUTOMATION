import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);
const PYTHON_DIR = path.join(process.cwd(), "python");
const PYTHON_BIN = path.join(PYTHON_DIR, "venv", "bin", "python3");

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
    const command = videoFileId
      ? `"${PYTHON_BIN}" "${path.join(PYTHON_DIR, "automation.py")}" upload "${videoFileId}"`
      : `"${PYTHON_BIN}" "${path.join(PYTHON_DIR, "automation.py")}" upload`;

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
