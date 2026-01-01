import { serve } from "inngest/next";
import { inngest } from "@/inngest/client";
import { 
  morningUpload, 
  afternoonUpload, 
  eveningUpload, 
  manualUpload, 
  dailyUpload 
} from "@/inngest/functions";

export const { GET, POST, PUT } = serve({
  client: inngest,
  functions: [
    morningUpload,    // 8:00 AM IST - All channels
    afternoonUpload,  // 1:00 PM IST - All channels  
    eveningUpload,    // 8:00 PM IST - All channels
    manualUpload,     // Manual trigger from UI
    dailyUpload       // Legacy (can be removed later)
  ],
});
