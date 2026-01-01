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

export async function GET(request: Request) {
  try {
    const { PYTHON_BIN, scriptPath } = getPythonPaths();
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "20";
    const channelId = searchParams.get("channelId") || "";
    let command = `"${PYTHON_BIN}" "${scriptPath}" videos ${limit}`;
    
    if (channelId) {
      command += ` "${channelId}"`;
    }
    
    const { stdout } = await execAsync(command);

    const videos = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: true,
      videos
    });
  } catch (error) {
    console.error("Failed to get videos:", error);
    return NextResponse.json(
      { success: false, error: "Failed to get videos" },
      { status: 500 }
    );
  }
}
