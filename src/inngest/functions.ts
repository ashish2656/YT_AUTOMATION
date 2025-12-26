import { inngest } from "./client";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);

// Daily upload function - runs at 6 PM IST (12:30 PM UTC)
export const dailyUpload = inngest.createFunction(
  { 
    id: "daily-youtube-upload",
    name: "Daily YouTube Upload"
  },
  { cron: "30 12 * * *" }, // 6 PM IST = 12:30 PM UTC
  async ({ event, step }) => {
    const result = await step.run("upload-video", async () => {
      const PYTHON_DIR = path.join(process.cwd(), "python");
      const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
      const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";
      const scriptPath = path.join(PYTHON_DIR, "automation.py");

      try {
        const { stdout, stderr } = await execAsync(
          `"${PYTHON_BIN}" "${scriptPath}" upload`
        );

        console.log("Upload output:", stdout);
        if (stderr) console.error("Upload stderr:", stderr);

        return JSON.parse(stdout.trim());
      } catch (error) {
        console.error("Upload failed:", error);
        throw error;
      }
    });

    return {
      success: result.success,
      videoId: result.videoId,
      fileName: result.fileName,
      youtubeUrl: result.youtubeUrl,
      uploadedAt: new Date().toISOString()
    };
  }
);

// Manual upload trigger
export const manualUpload = inngest.createFunction(
  { 
    id: "manual-youtube-upload",
    name: "Manual YouTube Upload"
  },
  { event: "youtube/upload.requested" },
  async ({ event, step }) => {
    const result = await step.run("upload-video", async () => {
      const PYTHON_DIR = path.join(process.cwd(), "python");
      const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
      const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";
      const scriptPath = path.join(PYTHON_DIR, "automation.py");

      const videoId = event.data?.videoId;
      const command = videoId
        ? `"${PYTHON_BIN}" "${scriptPath}" upload "${videoId}"`
        : `"${PYTHON_BIN}" "${scriptPath}" upload`;

      try {
        const { stdout, stderr } = await execAsync(command);
        console.log("Upload output:", stdout);
        if (stderr) console.error("Upload stderr:", stderr);
        return JSON.parse(stdout.trim());
      } catch (error) {
        console.error("Upload failed:", error);
        throw error;
      }
    });

    return result;
  }
);
