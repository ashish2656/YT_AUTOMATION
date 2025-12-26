import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);
const PYTHON_DIR = path.join(process.cwd(), "python");
const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "20";

    const scriptPath = path.join(PYTHON_DIR, "automation.py");
    const { stdout } = await execAsync(
      `"${PYTHON_BIN}" "${scriptPath}" videos ${limit}`
    );

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
