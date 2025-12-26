import { serve } from "inngest/next";
import { inngest } from "@/inngest/client";
import { dailyUpload, manualUpload } from "@/inngest/functions";

export const { GET, POST, PUT } = serve({
  client: inngest,
  functions: [dailyUpload, manualUpload],
});
