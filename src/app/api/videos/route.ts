import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);
const PYTHON_DIR = path.join(process.cwd(), "python");
const PYTHON_BIN = path.join(PYTHON_DIR, "venv", "bin", "python3");

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "20";

    const { stdout } = await execAsync(
      `"${PYTHON_BIN}" "${path.join(PYTHON_DIR, "automation.py")}" videos ${limit}`
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
