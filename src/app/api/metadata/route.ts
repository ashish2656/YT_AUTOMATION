import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);
const PYTHON_DIR = path.join(process.cwd(), "python");
const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";

// GET - Get trending metadata suggestions
export async function GET() {
  try {
    const scriptPath = path.join(PYTHON_DIR, "automation.py");
    const { stdout } = await execAsync(
      `"${PYTHON_BIN}" "${scriptPath}" metadata trending`
    );

    const data = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: true,
      ...data
    });
  } catch (error) {
    console.error("Failed to get trending metadata:", error);
    return NextResponse.json(
      { success: false, error: "Failed to get trending metadata" },
      { status: 500 }
    );
  }
}

// POST - Generate metadata for a specific channel
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { channelId, videoFilename } = body;

    const scriptPath = path.join(PYTHON_DIR, "automation.py");
    const command = `"${PYTHON_BIN}" "${scriptPath}" metadata generate ${channelId} ${videoFilename || ""}`;
    
    const { stdout } = await execAsync(command);
    const metadata = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: true,
      metadata
    });
  } catch (error) {
    console.error("Failed to generate metadata:", error);
    return NextResponse.json(
      { success: false, error: "Failed to generate metadata" },
      { status: 500 }
    );
  }
}
