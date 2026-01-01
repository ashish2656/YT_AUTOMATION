import { inngest } from "./client";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import { existsSync } from "fs";

const execAsync = promisify(exec);

// Helper function to get Python paths
function getPythonConfig() {
  const PYTHON_DIR = path.join(process.cwd(), "python");
  const VENV_PYTHON = path.join(PYTHON_DIR, "venv", "bin", "python3");
  const PYTHON_BIN = existsSync(VENV_PYTHON) ? VENV_PYTHON : "python3";
  const scriptPath = path.join(PYTHON_DIR, "automation.py");
  return { PYTHON_BIN, scriptPath };
}

// Helper function to upload from all channels
async function uploadFromAllChannels(): Promise<{
  success: boolean;
  results: Array<{ channel: string; success: boolean; videoId?: string; error?: string }>;
}> {
  const { PYTHON_BIN, scriptPath } = getPythonConfig();
  
  try {
    const { stdout, stderr } = await execAsync(
      `"${PYTHON_BIN}" "${scriptPath}" upload-all`
    );
    
    console.log("Upload-all output:", stdout);
    if (stderr) console.error("Upload-all stderr:", stderr);
    
    return JSON.parse(stdout.trim());
  } catch (error) {
    console.error("Upload-all failed:", error);
    throw error;
  }
}

// ============================================
// SCHEDULED UPLOADS - 3 videos/day per channel
// ============================================
// Optimal YouTube Shorts viewing times:
// - Morning:   8:00 AM IST (2:30 AM UTC) - Commute time
// - Afternoon: 1:00 PM IST (7:30 AM UTC) - Lunch break  
// - Evening:   8:00 PM IST (2:30 PM UTC) - Peak viewing
// ============================================

// Morning Upload - 8:00 AM IST (2:30 AM UTC)
export const morningUpload = inngest.createFunction(
  { 
    id: "morning-youtube-upload",
    name: "Morning Upload (8 AM IST) - All Channels"
  },
  { cron: "30 2 * * *" }, // 8:00 AM IST = 2:30 AM UTC
  async ({ step }) => {
    console.log("🌅 Starting morning upload for all channels...");
    
    const result = await step.run("upload-all-channels-morning", async () => {
      return await uploadFromAllChannels();
    });

    return {
      schedule: "morning",
      time: "8:00 AM IST",
      ...result,
      completedAt: new Date().toISOString()
    };
  }
);

// Afternoon Upload - 1:00 PM IST (7:30 AM UTC)
export const afternoonUpload = inngest.createFunction(
  { 
    id: "afternoon-youtube-upload",
    name: "Afternoon Upload (1 PM IST) - All Channels"
  },
  { cron: "30 7 * * *" }, // 1:00 PM IST = 7:30 AM UTC
  async ({ step }) => {
    console.log("☀️ Starting afternoon upload for all channels...");
    
    const result = await step.run("upload-all-channels-afternoon", async () => {
      return await uploadFromAllChannels();
    });

    return {
      schedule: "afternoon", 
      time: "1:00 PM IST",
      ...result,
      completedAt: new Date().toISOString()
    };
  }
);

// Evening Upload - 8:00 PM IST (2:30 PM UTC)
export const eveningUpload = inngest.createFunction(
  { 
    id: "evening-youtube-upload",
    name: "Evening Upload (8 PM IST) - All Channels"
  },
  { cron: "30 14 * * *" }, // 8:00 PM IST = 2:30 PM UTC
  async ({ step }) => {
    console.log("🌙 Starting evening upload for all channels...");
    
    const result = await step.run("upload-all-channels-evening", async () => {
      return await uploadFromAllChannels();
    });

    return {
      schedule: "evening",
      time: "8:00 PM IST", 
      ...result,
      completedAt: new Date().toISOString()
    };
  }
);

// Manual upload trigger (for UI button)
export const manualUpload = inngest.createFunction(
  { 
    id: "manual-youtube-upload",
    name: "Manual YouTube Upload"
  },
  { event: "youtube/upload.requested" },
  async ({ event, step }) => {
    const { PYTHON_BIN, scriptPath } = getPythonConfig();
    
    const result = await step.run("upload-video", async () => {
      const channelId = event.data?.channelId;
      const uploadAll = event.data?.uploadAll;
      
      let command: string;
      if (uploadAll) {
        command = `"${PYTHON_BIN}" "${scriptPath}" upload-all`;
      } else if (channelId) {
        command = `"${PYTHON_BIN}" "${scriptPath}" upload-next ${channelId}`;
      } else {
        command = `"${PYTHON_BIN}" "${scriptPath}" upload-next`;
      }

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

// Legacy daily upload (kept for backward compatibility, can be removed)
export const dailyUpload = inngest.createFunction(
  { 
    id: "daily-youtube-upload",
    name: "Daily YouTube Upload (Legacy)"
  },
  { cron: "30 12 * * *" }, // 6 PM IST = 12:30 PM UTC
  async ({ step }) => {
    const result = await step.run("upload-video", async () => {
      return await uploadFromAllChannels();
    });

    return {
      schedule: "legacy-daily",
      ...result,
      uploadedAt: new Date().toISOString()
    };
  }
);
