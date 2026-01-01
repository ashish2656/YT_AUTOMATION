import { NextResponse } from "next/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);

function getPythonPaths() {
  const PYTHON_DIR = path.join(process.cwd(), "python");
  const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
  const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";
  const scriptPath = path.join(PYTHON_DIR, "automation.py");
  return { PYTHON_BIN, scriptPath };
}

export async function GET() {
  try {
    const { PYTHON_BIN, scriptPath } = getPythonPaths();
    // Run Python script to get stats from Google Drive
    const { stdout } = await execAsync(
      `"${PYTHON_BIN}" "${scriptPath}" stats`
    );

    const stats = JSON.parse(stdout.trim());

    return NextResponse.json({
      success: true,
      stats: {
        total: stats.total,
        uploaded: stats.uploaded,
        pending: stats.pending
      }
    });
  } catch (error) {
    console.error("Failed to get stats:", error);
    return NextResponse.json(
      { success: false, error: "Failed to get stats" },
      { status: 500 }
    );
  }
}
