import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

function runPythonCommand(args: string[], timeoutMs = 30000): Promise<string> {
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

    // Add timeout
    const timeout = setTimeout(() => {
      proc.kill();
      reject(new Error("Command timed out"));
    }, timeoutMs);

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      clearTimeout(timeout);
      if (code !== 0) {
        reject(new Error(`Command failed: ${stderr || stdout}`));
      } else {
        resolve(stdout.trim());
      }
    });
  });
}

// GET - Get current token info
export async function GET() {
  try {
    const result = await runPythonCommand(["token-info"]);
    const data = JSON.parse(result);
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to get token info" },
      { status: 500 }
    );
  }
}

// POST - Save new token or switch account
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, token } = body;

    if (action === "switch") {
      // Clear token to switch accounts
      const result = await runPythonCommand(["switch-account"]);
      const data = JSON.parse(result);
      return NextResponse.json(data);
    } else if (action === "save" && token) {
      // Save new token
      const result = await runPythonCommand(["save-token", JSON.stringify(token)]);
      const data = JSON.parse(result);
      return NextResponse.json(data);
    } else {
      return NextResponse.json(
        { error: "Invalid action. Use 'switch' or 'save'" },
        { status: 400 }
      );
    }
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to process request" },
      { status: 500 }
    );
  }
}
