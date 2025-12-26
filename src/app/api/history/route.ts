import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

function runPythonCommand(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const pythonDir = path.join(process.cwd(), "python");
    const venvPython = path.join(pythonDir, "venv", "bin", "python3");
    const pythonPath = fs.existsSync(venvPython) ? venvPython : "python3";
    const scriptPath = path.join(pythonDir, "automation.py");

    const proc = spawn(pythonPath, [scriptPath, ...args], {
      cwd: pythonDir,
      env: { ...process.env },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`Command failed: ${stderr || stdout}`));
      } else {
        resolve(stdout.trim());
      }
    });
  });
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "50";
    
    const result = await runPythonCommand(["history", limit]);
    const data = JSON.parse(result);
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to get history" },
      { status: 500 }
    );
  }
}
