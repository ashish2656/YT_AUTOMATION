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

// GET current config
export async function GET() {
  try {
    const { PYTHON_BIN, scriptPath } = getPythonPaths();
    const { stdout } = await execAsync(
      `"${PYTHON_BIN}" "${scriptPath}" config`
    );

    const config = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: true,
      config
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
    const { PYTHON_BIN, scriptPath } = getPythonPaths();
    const body = await request.json();
    const { field, value } = body;

    let command: string;
    switch (field) {
      case "drive_folder_id":
        command = `"${PYTHON_BIN}" "${scriptPath}" set-folder "${value}"`;
        break;
      case "video_title":
        command = `"${PYTHON_BIN}" "${scriptPath}" set-title "${value}"`;
        break;
      case "video_description":
        command = `"${PYTHON_BIN}" "${scriptPath}" set-description "${value.replace(/"/g, '\\"')}"`;
        break;
      case "video_tags":
        const tags = Array.isArray(value) ? value.join(",") : value;
        command = `"${PYTHON_BIN}" "${scriptPath}" set-tags "${tags}"`;
        break;
      default:
        return NextResponse.json(
          { success: false, error: `Unknown field: ${field}` },
          { status: 400 }
        );
    }

    const { stdout } = await execAsync(command);
    const result = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: result.success || true,
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
