import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);

function getPythonPaths() {
  const PYTHON_DIR = path.join(process.cwd(), "python");
  const LOCAL_VENV = path.join(PYTHON_DIR, "venv", "bin", "python3");
  const RAILWAY_VENV = "/app/venv/bin/python3";
  const PYTHON_BIN = existsSync(LOCAL_VENV) ? LOCAL_VENV : (existsSync(RAILWAY_VENV) ? RAILWAY_VENV : "python3");
  const scriptPath = path.join(PYTHON_DIR, "automation.py");
  return { PYTHON_BIN, scriptPath };
}

export async function POST(request: Request) {
  try {
    const { PYTHON_BIN, scriptPath } = getPythonPaths();
    
    // Check if a specific video ID or channel was provided
    let videoFileId: string | null = null;
    let channelId: string = "";
    let uploadAll: boolean = false;
    
    try {
      const body = await request.json();
      videoFileId = body.videoId || null;
      channelId = body.channelId || "";
      uploadAll = body.uploadAll || false;
    } catch {
      // No body provided, use defaults
    }
    let command = "";
    
    // Upload from all channels
    if (uploadAll) {
      command = `"${PYTHON_BIN}" "${scriptPath}" upload-all`;
    } else if (videoFileId && channelId) {
      command = `"${PYTHON_BIN}" "${scriptPath}" upload "${videoFileId}" "${channelId}"`;
    } else if (channelId) {
      command = `"${PYTHON_BIN}" "${scriptPath}" upload "${channelId}"`;
    } else {
      return NextResponse.json(
        { success: false, error: "Channel ID is required" },
        { status: 400 }
      );
    }

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
