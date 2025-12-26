"use client";

import { motion } from "framer-motion";
import { 
  Upload, 
  Youtube, 
  FolderOpen, 
  Clock, 
  CheckCircle, 
  PlayCircle,
  Settings,
  RefreshCw,
  Zap
} from "lucide-react";
import { useState } from "react";

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "spring",
      stiffness: 100
    }
  }
};

const pulseVariants = {
  pulse: {
    scale: [1, 1.05, 1],
    transition: {
      duration: 2,
      repeat: Infinity
    }
  }
};

interface Video {
  id: string;
  name: string;
  size: string;
  status: "pending" | "uploading" | "uploaded";
}

export default function Dashboard() {
  const [videos, setVideos] = useState<Video[]>([
    { id: "1", name: "anime_edit_001.mp4", size: "2.9 MB", status: "uploaded" },
    { id: "2", name: "anime_edit_002.mp4", size: "1.4 MB", status: "uploaded" },
    { id: "3", name: "anime_edit_003.mp4", size: "1.7 MB", status: "pending" },
    { id: "4", name: "anime_edit_004.mp4", size: "5.1 MB", status: "pending" },
    { id: "5", name: "anime_edit_005.mp4", size: "5.5 MB", status: "pending" },
  ]);
  
  const [isUploading, setIsUploading] = useState(false);
  const [stats, setStats] = useState({
    total: 100,
    uploaded: 3,
    pending: 97
  });

  const handleUpload = async () => {
    setIsUploading(true);
    
    // Call the Python backend API
    try {
      const response = await fetch("/api/upload", { method: "POST" });
      const data = await response.json();
      
      if (data.success) {
        setStats(prev => ({
          ...prev,
          uploaded: prev.uploaded + 1,
          pending: prev.pending - 1
        }));
      }
    } catch (error) {
      console.error("Upload failed:", error);
    }
    
    setIsUploading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <motion.header 
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="border-b border-gray-800 bg-gray-950/50 backdrop-blur-lg sticky top-0 z-50"
      >
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              whileHover={{ rotate: 360 }}
              transition={{ duration: 0.5 }}
              className="p-2 bg-gradient-to-r from-red-600 to-pink-600 rounded-xl"
            >
              <Youtube className="w-6 h-6 text-white" />
            </motion.div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
              YT Automation
            </h1>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
          >
            <Settings className="w-5 h-5 text-gray-400" />
          </motion.button>
        </div>
      </motion.header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-8"
        >
          {/* Stats Cards */}
          <motion.div 
            variants={itemVariants}
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            {/* Total Videos */}
            <motion.div 
              whileHover={{ scale: 1.02, y: -5 }}
              className="p-6 rounded-2xl bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-800 backdrop-blur"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Total Videos</p>
                  <p className="text-3xl font-bold mt-1">{stats.total}</p>
                </div>
                <div className="p-3 bg-blue-500/20 rounded-xl">
                  <FolderOpen className="w-6 h-6 text-blue-400" />
                </div>
              </div>
            </motion.div>

            {/* Uploaded */}
            <motion.div 
              whileHover={{ scale: 1.02, y: -5 }}
              className="p-6 rounded-2xl bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-800 backdrop-blur"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Uploaded</p>
                  <p className="text-3xl font-bold mt-1 text-green-400">{stats.uploaded}</p>
                </div>
                <div className="p-3 bg-green-500/20 rounded-xl">
                  <CheckCircle className="w-6 h-6 text-green-400" />
                </div>
              </div>
            </motion.div>

            {/* Pending */}
            <motion.div 
              whileHover={{ scale: 1.02, y: -5 }}
              className="p-6 rounded-2xl bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-800 backdrop-blur"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Pending</p>
                  <p className="text-3xl font-bold mt-1 text-yellow-400">{stats.pending}</p>
                </div>
                <div className="p-3 bg-yellow-500/20 rounded-xl">
                  <Clock className="w-6 h-6 text-yellow-400" />
                </div>
              </div>
            </motion.div>
          </motion.div>

          {/* Upload Section */}
          <motion.div 
            variants={itemVariants}
            className="p-6 rounded-2xl bg-gradient-to-br from-gray-800/30 to-gray-900/30 border border-gray-800"
          >
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold">Quick Upload</h2>
                <p className="text-gray-400 text-sm mt-1">
                  Upload the next video from your Google Drive folder
                </p>
              </div>
              <motion.button
                onClick={handleUpload}
                disabled={isUploading}
                variants={pulseVariants}
                animate={!isUploading ? "pulse" : ""}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`px-8 py-4 rounded-xl font-semibold flex items-center gap-3 transition-all ${
                  isUploading 
                    ? "bg-gray-700 cursor-not-allowed" 
                    : "bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500 shadow-lg shadow-red-500/25"
                }`}
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Upload Next Video
                  </>
                )}
              </motion.button>
            </div>

            {/* Progress bar when uploading */}
            {isUploading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6"
              >
                <div className="flex justify-between text-sm text-gray-400 mb-2">
                  <span>Uploading to YouTube...</span>
                  <span>Processing</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 3, ease: "linear" }}
                    className="h-full bg-gradient-to-r from-red-600 to-pink-600"
                  />
                </div>
              </motion.div>
            )}
          </motion.div>

          {/* Video Queue */}
          <motion.div variants={itemVariants}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Video Queue</h2>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </motion.button>
            </div>

            <div className="space-y-3">
              {videos.map((video, index) => (
                <motion.div
                  key={video.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.01, x: 5 }}
                  className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50 flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg ${
                      video.status === "uploaded" 
                        ? "bg-green-500/20" 
                        : video.status === "uploading"
                        ? "bg-yellow-500/20"
                        : "bg-gray-700"
                    }`}>
                      {video.status === "uploaded" ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : video.status === "uploading" ? (
                        <RefreshCw className="w-5 h-5 text-yellow-400 animate-spin" />
                      ) : (
                        <PlayCircle className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium">{video.name}</p>
                      <p className="text-sm text-gray-500">{video.size}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      video.status === "uploaded"
                        ? "bg-green-500/20 text-green-400"
                        : video.status === "uploading"
                        ? "bg-yellow-500/20 text-yellow-400"
                        : "bg-gray-700 text-gray-400"
                    }`}>
                      {video.status === "uploaded" ? "Uploaded" : video.status === "uploading" ? "Uploading" : "Pending"}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Settings Preview */}
          <motion.div 
            variants={itemVariants}
            className="p-6 rounded-2xl bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-800/30"
          >
            <div className="flex items-center gap-3 mb-4">
              <Zap className="w-5 h-5 text-purple-400" />
              <h3 className="font-bold">Upload Settings</h3>
            </div>
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <div className="p-3 rounded-lg bg-gray-800/50">
                <p className="text-gray-400">Title</p>
                <p className="font-medium mt-1">Anime Edits #Shorts</p>
              </div>
              <div className="p-3 rounded-lg bg-gray-800/50">
                <p className="text-gray-400">Category</p>
                <p className="font-medium mt-1">Entertainment</p>
              </div>
              <div className="p-3 rounded-lg bg-gray-800/50 md:col-span-2">
                <p className="text-gray-400">Tags</p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {["AnimeEdits", "AnimeEdit", "OtakuVibes", "AnimeLovers", "Shorts"].map((tag) => (
                    <span key={tag} className="px-2 py-1 rounded bg-purple-500/20 text-purple-300 text-xs">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-12 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-gray-500 text-sm">
          YouTube Automation Dashboard • Built with Next.js & Framer Motion
        </div>
      </footer>
    </div>
  );
}
