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

// GET - Get all channels configuration
export async function GET() {
  try {
    const { PYTHON_BIN, scriptPath } = getPythonPaths();
    const { stdout } = await execAsync(
      `"${PYTHON_BIN}" "${scriptPath}" channels list`
    );

    const result = JSON.parse(stdout.trim());

    return NextResponse.json(result);
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
    const { PYTHON_BIN, scriptPath } = getPythonPaths();
    const body = await request.json();
    const { action, channelId, channelData } = body;
    
    let command = "";
    if (action === "update") {
      command = `"${PYTHON_BIN}" "${scriptPath}" channels update ${channelId} '${JSON.stringify(channelData)}'`;
    } else if (action === "create") {
      command = `"${PYTHON_BIN}" "${scriptPath}" channels create '${JSON.stringify(channelData)}'`;
    } else if (action === "delete") {
      command = `"${PYTHON_BIN}" "${scriptPath}" channels delete ${channelId}`;
    } else if (action === "toggle") {
      command = `"${PYTHON_BIN}" "${scriptPath}" channels toggle ${channelId}`;
    } else {
      return NextResponse.json(
        { success: false, error: "Invalid action" },
        { status: 400 }
      );
    }

    const { stdout } = await execAsync(command);
    const result = JSON.parse(stdout.trim());

    return NextResponse.json(result);
  } catch (error) {
    console.error("Failed to update channels:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update channels" },
      { status: 500 }
    );
  }
}
