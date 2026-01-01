"use client";

import { motion, Variants } from "framer-motion";
import { 
  Upload, 
  Youtube, 
  FolderOpen, 
  Clock, 
  CheckCircle, 
  PlayCircle,
  Settings,
  RefreshCw,
  Zap,
  X,
  Save,
  Link,
  AlertCircle,
  User,
  LogOut,
  History,
  Plus,
  Edit,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Folder,
  Tag
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";

// Animation variants
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants: Variants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      type: "spring" as const,
      stiffness: 100
    }
  }
};

const pulseVariants: Variants = {
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

interface Config {
  drive_folder_id: string;
  video_title: string;
  video_description: string;
  video_tags: string[];
}

interface Channel {
  id: string;
  name: string;
  drive_folder_id: string;
  youtube_account?: string;
  enabled: boolean;
  categories: string[];
  templates: {
    title: string;
    description: string;
  };
  uploaded_count?: number;
}

export default function Dashboard() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);
  const [stats, setStats] = useState({
    total: 0,
    uploaded: 0,
    pending: 0
  });
  const [config, setConfig] = useState<Config>({
    drive_folder_id: "",
    video_title: "",
    video_description: "",
    video_tags: []
  });
  const [isSaving, setIsSaving] = useState(false);
  const [accountInfo, setAccountInfo] = useState<{hasToken: boolean; account?: string; expiry?: string}>({hasToken: false});
  const [isSwitchingAccount, setIsSwitchingAccount] = useState(false);
  const [newToken, setNewToken] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [uploadHistory, setUploadHistory] = useState<{file_name: string; youtube_url: string; uploaded_at: string}[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [showChannels, setShowChannels] = useState(false);
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>("");
  const [channelForm, setChannelForm] = useState({
    name: "",
    drive_folder_id: "",
    youtube_account: "account1",
    categories: "",
    title_template: "{trending_title}",
    description_template: "{trending_description}\n\n#shorts"
  });

  // Fetch stats from API
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch("/api/stats");
      const data = await response.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    }
  }, []);

  // Fetch videos from API
  const fetchVideos = useCallback(async (channelId?: string) => {
    try {
      const url = channelId 
        ? `/api/videos?limit=20&channelId=${channelId}`
        : `/api/videos?limit=20`;
      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setVideos(data.videos);
      }
    } catch (error) {
      console.error("Failed to fetch videos:", error);
    }
  }, []);

  // Fetch config from API
  const fetchConfig = useCallback(async () => {
    try {
      const response = await fetch("/api/config");
      const data = await response.json();
      if (data.success) {
        setConfig(data.config);
      }
    } catch (error) {
      console.error("Failed to fetch config:", error);
    }
  }, []);

  // Fetch account info
  const fetchAccountInfo = useCallback(async () => {
    try {
      const response = await fetch("/api/account");
      const data = await response.json();
      setAccountInfo(data);
    } catch (error) {
      console.error("Failed to fetch account info:", error);
    }
  }, []);

  // Fetch upload history
  const fetchHistory = useCallback(async () => {
    try {
      const response = await fetch("/api/history?limit=20");
      const data = await response.json();
      if (data.success && Array.isArray(data.history)) {
        setUploadHistory(data.history.map((h: { title?: string; file_name?: string; youtube_url?: string; uploaded_at?: string }) => ({
          file_name: h.title || h.file_name || 'Unknown',
          youtube_url: h.youtube_url || '',
          uploaded_at: h.uploaded_at || ''
        })));
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    }
  }, []);

  // Fetch channels
  const fetchChannels = useCallback(async () => {
    try {
      console.log('Fetching channels...');
      const response = await fetch("/api/channels");
      const data = await response.json();
      console.log('Channels response:', data);
      
      if (data.success && Array.isArray(data.channels)) {
        console.log('Setting channels:', data.channels.length, 'channels');
        setChannels(data.channels);
        // Auto-select first channel if none selected
        if (!selectedChannel && data.channels.length > 0) {
          setSelectedChannel(data.channels[0].id);
        }
      } else {
        console.warn('Invalid channels response, setting empty array');
        setChannels([]);
      }
    } catch (error) {
      console.error("Failed to fetch channels:", error);
      setChannels([]);
    }
  }, [selectedChannel]);

  // Create or update channel
  const saveChannel = async () => {
    try {
      const channelData = {
        name: channelForm.name,
        drive_folder_id: channelForm.drive_folder_id,
        youtube_account: channelForm.youtube_account,
        categories: channelForm.categories.split(",").map(c => c.trim()).filter(Boolean),
        templates: {
          title: channelForm.title_template,
          description: channelForm.description_template
        },
        enabled: true
      };

      const action = editingChannel ? "update" : "create";
      const body: any = { action, channelData };
      if (editingChannel) {
        body.channelId = editingChannel.id;
      }

      console.log('Saving channel:', action, channelData);

      const response = await fetch("/api/channels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      const data = await response.json();
      console.log('Save response:', data);
      
      if (data.success) {
        console.log('Channel saved successfully, refreshing list...');
        await fetchChannels();
        setShowChannelModal(false);
        setEditingChannel(null);
        setChannelForm({
          name: "",
          drive_folder_id: "",
          youtube_account: "account1",
          categories: "",
          title_template: "{trending_title}",
          description_template: "{trending_description}\n\n#shorts"
        });
      } else {
        console.error('Failed to save channel:', data.error);
        alert('Failed to save channel: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error("Failed to save channel:", error);
      alert('Failed to save channel. Check console for details.');
    }
  };

  // Delete channel
  const deleteChannel = async (channelId: string) => {
    if (!confirm("Are you sure you want to delete this channel?")) return;
    try {
      const response = await fetch("/api/channels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete", channelId })
      });
      const data = await response.json();
      if (data.success) {
        fetchChannels();
      }
    } catch (error) {
      console.error("Failed to delete channel:", error);
    }
  };

  // Toggle channel
  const toggleChannel = async (channelId: string) => {
    try {
      const response = await fetch("/api/channels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "toggle", channelId })
      });
      const data = await response.json();
      if (data.success) {
        fetchChannels();
      }
    } catch (error) {
      console.error("Failed to toggle channel:", error);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchStats();
    fetchVideos();
    fetchConfig();
    fetchAccountInfo();
    fetchHistory();
    fetchChannels();
  }, [fetchStats, fetchVideos, fetchConfig, fetchAccountInfo, fetchHistory, fetchChannels]);

  // Fetch videos when selected channel changes
  useEffect(() => {
    if (selectedChannel) {
      fetchVideos(selectedChannel);
    }
  }, [selectedChannel, fetchVideos]);

  // Refresh all data
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([
      fetchStats(), 
      fetchVideos(selectedChannel), 
      fetchConfig(), 
      fetchAccountInfo(), 
      fetchHistory(), 
      fetchChannels()
    ]);
    setIsRefreshing(false);
  };

  // Switch YouTube account
  const handleSwitchAccount = async () => {
    setIsSwitchingAccount(true);
    try {
      const response = await fetch("/api/account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "switch" })
      });
      const data = await response.json();
      if (data.success) {
        setShowTokenInput(true);
        setAccountInfo({ hasToken: false });
      }
    } catch (error) {
      console.error("Failed to switch account:", error);
    }
    setIsSwitchingAccount(false);
  };

  // Save new token
  const handleSaveToken = async () => {
    if (!newToken.trim()) return;
    
    setIsSaving(true);
    try {
      const tokenData = JSON.parse(newToken);
      const response = await fetch("/api/account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "save", token: tokenData })
      });
      const data = await response.json();
      if (data.success) {
        setShowTokenInput(false);
        setNewToken("");
        await fetchAccountInfo();
        setUploadMessage({ type: 'success', text: 'YouTube account updated successfully!' });
      } else {
        setUploadMessage({ type: 'error', text: data.error || 'Failed to save token' });
      }
    } catch (error) {
      setUploadMessage({ type: 'error', text: 'Invalid token JSON format' });
    }
    setIsSaving(false);
  };

  // Upload next video - Not available on Vercel, show message
  const handleUpload = async () => {
    setUploadMessage({ 
      type: 'error', 
      text: 'Manual uploads not available. Uploads run automatically via GitHub Actions at 8AM, 1PM, 8PM IST. Go to GitHub → Actions tab to trigger manually.' 
    });
    setTimeout(() => setUploadMessage(null), 8000);
  };

  // Upload from all channels - Not available on Vercel
  const [isUploadingAll, setIsUploadingAll] = useState(false);
  const handleUploadAll = async () => {
    setUploadMessage({ 
      type: 'error', 
      text: 'Manual uploads not available. Uploads run automatically via GitHub Actions at 8AM, 1PM, 8PM IST. Go to GitHub → Actions tab to trigger manually.' 
    });
    setTimeout(() => setUploadMessage(null), 8000);
  };

  // Save config
  const handleSaveConfig = async (field: string, value: string | string[]) => {
    setIsSaving(true);
    try {
      const response = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field, value })
      });
      const data = await response.json();
      if (data.success) {
        await fetchConfig();
      }
    } catch (error) {
      console.error("Failed to save config:", error);
    }
    setIsSaving(false);
  };

  // Extract folder ID from Google Drive link
  const extractFolderId = (input: string): string => {
    // If it's already just an ID, return it
    if (!input.includes('/')) return input;
    
    // Extract from various Drive URL formats
    const patterns = [
      /\/folders\/([a-zA-Z0-9_-]+)/,
      /id=([a-zA-Z0-9_-]+)/,
      /\/d\/([a-zA-Z0-9_-]+)/
    ];
    
    for (const pattern of patterns) {
      const match = input.match(pattern);
      if (match) return match[1];
    }
    
    return input;
  };

  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <motion.header 
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="border-b border-white/10 glass-effect sticky top-0 z-50 shine-effect"
      >
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              whileHover={{ rotate: 360, scale: 1.1 }}
              transition={{ duration: 0.5 }}
              className="p-3 bg-gradient-to-br from-white/20 to-white/5 rounded-2xl shadow-lg border border-white/20"
              style={{
                boxShadow: '0 8px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.3)'
              }}
            >
              <Youtube className="w-6 h-6 text-white drop-shadow-lg" />
            </motion.div>
            <h1 className="text-2xl font-bold text-white drop-shadow-2xl tracking-tight">
              YT Automation
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <motion.button
              onClick={() => setShowChannels(true)}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className="p-2.5 rounded-xl glass-effect hover:bg-white/10 transition-all"
            >
              <Folder className="w-5 h-5 text-white/90" />
            </motion.button>
            <motion.button
              onClick={() => setShowHistory(true)}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className="p-2.5 rounded-xl glass-effect hover:bg-white/10 transition-all"
            >
              <History className="w-5 h-5 text-white/90" />
            </motion.button>
            <motion.button
              onClick={handleRefresh}
              disabled={isRefreshing}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className="p-2.5 rounded-xl glass-effect hover:bg-white/10 transition-all"
            >
              <RefreshCw className={`w-5 h-5 text-white/90 ${isRefreshing ? 'animate-spin' : ''}`} />
            </motion.button>
            <motion.button
              onClick={() => setShowSettings(true)}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              className="p-2.5 rounded-xl glass-effect hover:bg-white/10 transition-all"
            >
              <Settings className="w-5 h-5 text-white/90" />
            </motion.button>
          </div>
        </div>
      </motion.header>

      {/* History Modal */}
      {showHistory && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/90 backdrop-blur-xl z-50 flex items-center justify-center p-4"
          onClick={() => setShowHistory(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="glass-effect rounded-3xl p-8 w-full max-w-2xl max-h-[90vh] overflow-y-auto shine-effect"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold flex items-center gap-3 text-white">
                <History className="w-6 h-6" />
                Upload History
              </h2>
              <button 
                onClick={() => setShowHistory(false)}
                className="p-2 rounded-xl glass-effect hover:bg-white/10 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              {uploadHistory.length === 0 ? (
                <p className="text-white/60 text-center py-8">No uploads yet</p>
              ) : (
                uploadHistory.map((item, i) => (
                  <div key={i} className="p-4 rounded-2xl glass-effect hover:bg-white/5 transition-all">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate text-white">{item.file_name}</p>
                        <p className="text-xs text-white/50 mt-1">
                          {item.uploaded_at ? new Date(item.uploaded_at).toLocaleString() : 'Unknown date'}
                        </p>
                      </div>
                      {item.youtube_url && (
                        <a
                          href={item.youtube_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-4 px-4 py-2 rounded-xl glass-effect hover:bg-white/20 text-sm flex items-center gap-2 transition-all"
                        >
                          <Youtube className="w-4 h-4" />
                          View
                        </a>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Settings Modal */}
      {showSettings && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/90 backdrop-blur-xl z-50 flex items-center justify-center p-4"
          onClick={() => setShowSettings(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="glass-effect rounded-3xl p-8 w-full max-w-2xl max-h-[90vh] overflow-y-auto shine-effect"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white">Settings</h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="p-2 rounded-xl glass-effect hover:bg-white/10 transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-6">
              {/* Google Drive Folder */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">
                  <Link className="w-4 h-4 inline mr-2" />
                  Google Drive Folder Link or ID
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={config.drive_folder_id}
                    onChange={(e) => setConfig(prev => ({ ...prev, drive_folder_id: e.target.value }))}
                    placeholder="Paste Google Drive folder link or ID"
                    className="flex-1 px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:ring-2 focus:ring-white/30 focus:outline-none transition-all"
                  />
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      const folderId = extractFolderId(config.drive_folder_id);
                      handleSaveConfig("drive_folder_id", folderId);
                    }}
                    disabled={isSaving}
                    className="px-4 py-3 rounded-xl glass-effect hover:bg-white/20 transition-all flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    Save
                  </motion.button>
                </div>
                <p className="text-xs text-white/40 mt-2">
                  Paste the full Google Drive folder link or just the folder ID
                </p>
              </div>

              {/* Video Title */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">
                  Video Title
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={config.video_title}
                    onChange={(e) => setConfig(prev => ({ ...prev, video_title: e.target.value }))}
                    placeholder="Enter video title"
                    className="flex-1 px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:ring-2 focus:ring-white/30 focus:outline-none transition-all"
                  />
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleSaveConfig("video_title", config.video_title)}
                    disabled={isSaving}
                    className="px-4 py-3 rounded-xl glass-effect hover:bg-white/20 transition-all flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    Save
                  </motion.button>
                </div>
              </div>

              {/* Video Description */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">
                  Video Description
                </label>
                <div className="flex gap-2">
                  <textarea
                    value={config.video_description}
                    onChange={(e) => setConfig(prev => ({ ...prev, video_description: e.target.value }))}
                    placeholder="Enter video description"
                    rows={4}
                    className="flex-1 px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:ring-2 focus:ring-white/30 focus:outline-none transition-all resize-none"
                  />
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleSaveConfig("video_description", config.video_description)}
                    disabled={isSaving}
                    className="px-4 py-3 rounded-xl glass-effect hover:bg-white/20 transition-all flex items-center gap-2 self-start"
                  >
                    <Save className="w-4 h-4" />
                    Save
                  </motion.button>
                </div>
              </div>

              {/* Video Tags */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">
                  Video Tags (comma-separated)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={config.video_tags?.join(", ") || ""}
                    onChange={(e) => setConfig(prev => ({ 
                      ...prev, 
                      video_tags: e.target.value.split(",").map(t => t.trim()).filter(Boolean)
                    }))}
                    placeholder="tag1, tag2, tag3"
                    className="flex-1 px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:ring-2 focus:ring-white/30 focus:outline-none transition-all"
                  />
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleSaveConfig("video_tags", config.video_tags)}
                    disabled={isSaving}
                    className="px-4 py-3 rounded-xl glass-effect hover:bg-white/20 transition-all flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    Save
                  </motion.button>
                </div>
                <div className="flex flex-wrap gap-2 mt-3">
                  {config.video_tags?.map((tag, i) => (
                    <span key={i} className="px-3 py-1 rounded-full glass-effect text-white/90 text-xs">
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Divider */}
              <div className="border-t border-white/10 pt-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
                  <User className="w-5 h-5" />
                  YouTube Account
                </h3>

                {/* Account Status */}
                <div className="p-4 rounded-xl glass-effect mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-white/60">Status</p>
                      <p className={`font-medium ${accountInfo.hasToken ? 'text-white' : 'text-white/70'}`}>
                        {accountInfo.hasToken ? '✓ Connected' : '⚠ Not Connected'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Token Input (shown after switch) */}
                {showTokenInput && (
                  <div className="space-y-3">
                    <p className="text-sm text-white/70">
                      Run this command locally to get a new token:
                    </p>
                    <code className="block p-3 rounded-lg bg-black/50 text-xs text-white/80 overflow-x-auto">
                      python3 automation.py stats
                    </code>
                    <p className="text-sm text-white/60">
                      Then paste the contents of token.json below:
                    </p>
                    <textarea
                      value={newToken}
                      onChange={(e) => setNewToken(e.target.value)}
                      placeholder='{"token": "...", "refresh_token": "...", ...}'
                      rows={4}
                      className="w-full px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:ring-2 focus:ring-white/30 focus:outline-none transition-all resize-none font-mono text-xs"
                    />
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={handleSaveToken}
                      disabled={isSaving || !newToken.trim()}
                      className="w-full py-3 rounded-xl glass-effect hover:bg-white/20 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                    >
                      <Save className="w-4 h-4" />
                      {isSaving ? 'Saving...' : 'Save New Token'}
                    </motion.button>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-8"
        >
          {/* Upload Message */}
          {uploadMessage && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={`p-4 rounded-xl glass-effect flex items-center gap-3 ${
                uploadMessage.type === 'success' 
                  ? 'text-white'
                  : 'text-white/90'
              }`}
            >
              {uploadMessage.type === 'success' ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              {uploadMessage.text}
            </motion.div>
          )}

          {/* Stats Cards */}
          <motion.div 
            variants={itemVariants}
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            {/* Total Videos */}
            <motion.div 
              whileHover={{ scale: 1.02, y: -5 }}
              className="p-6 rounded-2xl glass-effect shine-effect backdrop-blur-xl"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/60 text-sm">Total Videos</p>
                  <p className="text-4xl font-bold mt-1 text-white drop-shadow-lg">{stats.total}</p>
                </div>
                <div className="p-4 bg-white/10 rounded-2xl border border-white/20">
                  <FolderOpen className="w-7 h-7 text-white" />
                </div>
              </div>
            </motion.div>

            {/* Uploaded */}
            <motion.div 
              whileHover={{ scale: 1.02, y: -5 }}
              className="p-6 rounded-2xl glass-effect shine-effect backdrop-blur-xl"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/60 text-sm">Uploaded</p>
                  <p className="text-4xl font-bold mt-1 text-white drop-shadow-lg">{stats.uploaded}</p>
                </div>
                <div className="p-4 bg-white/10 rounded-2xl border border-white/20">
                  <CheckCircle className="w-7 h-7 text-white" />
                </div>
              </div>
            </motion.div>

            {/* Pending */}
            <motion.div 
              whileHover={{ scale: 1.02, y: -5 }}
              className="p-6 rounded-2xl glass-effect shine-effect backdrop-blur-xl"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/60 text-sm">Pending</p>
                  <p className="text-4xl font-bold mt-1 text-white drop-shadow-lg">{stats.pending}</p>
                </div>
                <div className="p-4 bg-white/10 rounded-2xl border border-white/20">
                  <Clock className="w-7 h-7 text-white" />
                </div>
              </div>
            </motion.div>
          </motion.div>

          {/* Upload Section */}
          <motion.div 
            variants={itemVariants}
            className="p-8 rounded-2xl glass-effect shine-effect"
          >
            <div className="flex flex-col gap-6">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-white">Quick Upload</h2>
                  <p className="text-white/60 text-sm mt-1">
                    Select account and upload the next pending video from Drive
                  </p>
                </div>
                
                {/* Channel Selector */}
                <div className="flex items-center gap-3">
                  <label className="text-white/70 text-sm font-medium">Channel:</label>
                  <select
                    value={selectedChannel}
                    onChange={(e) => setSelectedChannel(e.target.value)}
                    className="px-4 py-2 rounded-xl glass-effect text-white border border-white/20 focus:border-white/40 focus:outline-none min-w-[200px]"
                  >
                    {channels.length === 0 ? (
                      <option value="">No channels configured</option>
                    ) : (
                      channels
                        .filter(ch => ch.enabled && ch.drive_folder_id)
                        .map(ch => (
                          <option key={ch.id} value={ch.id}>
                            {ch.name} ({ch.youtube_account || 'No account'})
                          </option>
                        ))
                    )}
                  </select>
                </div>
              </div>
              
              <div className="flex items-center justify-center">
                <motion.button
                  onClick={handleUpload}
                  disabled={isUploading || !selectedChannel || channels.filter(ch => ch.enabled && ch.drive_folder_id).length === 0}
                  variants={pulseVariants}
                  animate={!isUploading && selectedChannel ? "pulse" : ""}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`px-8 py-4 rounded-xl font-semibold flex items-center gap-3 transition-all ${
                    isUploading || !selectedChannel || channels.filter(ch => ch.enabled && ch.drive_folder_id).length === 0
                      ? "glass-effect opacity-50 cursor-not-allowed" 
                    : "glass-effect hover:bg-white/20 shadow-xl shine-effect"
                }`}
                style={{
                  boxShadow: isUploading || stats.pending === 0 ? '' : '0 8px 24px rgba(255,255,255,0.1), inset 0 1px 0 rgba(255,255,255,0.3)'
                }}
              >
                {isUploading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Uploading...
                  </>
                ) : stats.pending === 0 ? (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    All Uploaded!
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Upload Next Video
                  </>
                )}
              </motion.button>

                {/* Upload All Channels Button */}
                <motion.button
                  onClick={handleUploadAll}
                  disabled={isUploadingAll || channels.filter(ch => ch.enabled && ch.drive_folder_id).length === 0}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`px-8 py-4 rounded-xl font-semibold flex items-center gap-3 transition-all ${
                    isUploadingAll || channels.filter(ch => ch.enabled && ch.drive_folder_id).length === 0
                      ? "glass-effect opacity-50 cursor-not-allowed" 
                      : "bg-gradient-to-r from-purple-500/20 to-pink-500/20 hover:from-purple-500/30 hover:to-pink-500/30 border border-purple-400/30 shadow-xl"
                  }`}
                >
                  {isUploadingAll ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Uploading All...
                    </>
                  ) : (
                    <>
                      <Zap className="w-5 h-5 text-purple-300" />
                      Upload All Channels
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
                <div className="flex justify-between text-sm text-white/60 mb-2">
                  <span>Uploading to YouTube...</span>
                  <span>Processing</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 30, ease: "linear" }}
                    className="h-full bg-gradient-to-r from-white/80 to-white/40"
                  />
                </div>
              </motion.div>
            )}
          </div>
          </motion.div>

          {/* Video Queue */}
          <motion.div variants={itemVariants}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-white">Video Queue</h2>
              <motion.button
                onClick={handleRefresh}
                disabled={isRefreshing}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-4 py-2 rounded-xl glass-effect hover:bg-white/10 transition-all text-sm flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </motion.button>
            </div>

            <div className="space-y-3">
              {videos.length === 0 ? (
                <div className="p-12 text-center text-white/50 glass-effect rounded-2xl">
                  <FolderOpen className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No videos found. Click refresh to load videos from Google Drive.</p>
                </div>
              ) : (
                videos.map((video, index) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    whileHover={{ scale: 1.01, x: 5 }}
                    className="p-5 rounded-2xl glass-effect flex items-center justify-between hover:bg-white/5 transition-all"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`p-3 rounded-xl ${
                        video.status === "uploaded" 
                          ? "bg-white/20 border border-white/30" 
                          : video.status === "uploading"
                          ? "bg-white/15 border border-white/20"
                          : "bg-white/5 border border-white/10"
                      }`}>
                        {video.status === "uploaded" ? (
                          <CheckCircle className="w-5 h-5 text-white" />
                        ) : video.status === "uploading" ? (
                          <RefreshCw className="w-5 h-5 text-white animate-spin" />
                        ) : (
                          <PlayCircle className="w-5 h-5 text-white/70" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium truncate max-w-[200px] md:max-w-none text-white">{video.name}</p>
                        <p className="text-sm text-white/50">{video.size}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-4 py-2 rounded-full text-xs font-medium ${
                        video.status === "uploaded"
                          ? "bg-white/20 text-white border border-white/30"
                          : video.status === "uploading"
                          ? "bg-white/15 text-white border border-white/20"
                          : "bg-white/5 text-white/60 border border-white/10"
                      }`}>
                        {video.status === "uploaded" ? "Uploaded" : video.status === "uploading" ? "Uploading" : "Pending"}
                      </span>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-12 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-white/50 text-sm">
          YouTube Automation Dashboard • Built with Next.js & Framer Motion
        </div>
      </footer>

      {/* Channels Modal */}
      {showChannels && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/90 backdrop-blur-xl z-50 flex items-center justify-center p-4"
          onClick={() => setShowChannels(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="glass-effect rounded-3xl p-8 w-full max-w-4xl max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold text-white flex items-center gap-3">
                <Folder className="w-8 h-8" />
                YouTube Channels
              </h2>
              <div className="flex gap-2">
                <motion.button
                  onClick={() => {
                    setEditingChannel(null);
                    setChannelForm({
                      name: "",
                      drive_folder_id: "",
                      youtube_account: "account1",
                      categories: "",
                      title_template: "{trending_title}",
                      description_template: "{trending_description}\n\n#shorts"
                    });
                    setShowChannelModal(true);
                  }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-4 py-2 rounded-xl bg-white/20 hover:bg-white/30 text-white flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  New Channel
                </motion.button>
                <motion.button
                  onClick={() => setShowChannels(false)}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  className="p-2 rounded-xl bg-white/10 hover:bg-white/20"
                >
                  <X className="w-5 h-5 text-white" />
                </motion.button>
              </div>
            </div>

            <div className="space-y-4">
              {!Array.isArray(channels) || channels.length === 0 ? (
                <div className="p-12 text-center text-white/50">
                  <Folder className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No channels configured yet. Click "New Channel" to add one.</p>
                </div>
              ) : (
                channels.map((channel) => (
                  <motion.div
                    key={channel.id}
                    whileHover={{ scale: 1.01 }}
                    className="p-6 rounded-2xl glass-effect"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-xl font-bold text-white">{channel.name}</h3>
                          {channel.enabled ? (
                            <span className="px-2 py-1 rounded-full bg-green-500/20 text-green-300 text-xs">Active</span>
                          ) : (
                            <span className="px-2 py-1 rounded-full bg-red-500/20 text-red-300 text-xs">Disabled</span>
                          )}
                        </div>
                        <div className="space-y-2 text-sm">
                          <div className="flex items-center gap-2 text-white/70">
                            <FolderOpen className="w-4 h-4" />
                            <span className="font-mono">{channel.drive_folder_id}</span>
                          </div>
                          {channel.categories && channel.categories.length > 0 && (
                            <div className="flex items-center gap-2 text-white/70">
                              <Tag className="w-4 h-4" />
                              <div className="flex flex-wrap gap-1">
                                {channel.categories.map((cat) => (
                                  <span key={cat} className="px-2 py-0.5 rounded-full bg-white/10 text-xs">
                                    {cat}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="flex items-center gap-2 text-white/70">
                            <Upload className="w-4 h-4" />
                            <span className="text-green-400 font-semibold">{channel.uploaded_count || 0}</span>
                            <span>videos uploaded</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <motion.button
                          onClick={() => toggleChannel(channel.id)}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 rounded-xl bg-white/10 hover:bg-white/20"
                        >
                          {channel.enabled ? (
                            <ToggleRight className="w-5 h-5 text-green-400" />
                          ) : (
                            <ToggleLeft className="w-5 h-5 text-white/40" />
                          )}
                        </motion.button>
                        <motion.button
                          onClick={() => {
                            setEditingChannel(channel);
                            setChannelForm({
                              name: channel.name,
                              drive_folder_id: channel.drive_folder_id,
                              youtube_account: channel.youtube_account || "account1",
                              categories: channel.categories.join(", "),
                              title_template: channel.templates?.title || "{trending_title}",
                              description_template: channel.templates?.description || "{trending_description}\n\n#shorts"
                            });
                            setShowChannelModal(true);
                          }}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 rounded-xl bg-white/10 hover:bg-white/20"
                        >
                          <Edit className="w-5 h-5 text-blue-400" />
                        </motion.button>
                        <motion.button
                          onClick={() => deleteChannel(channel.id)}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 rounded-xl bg-white/10 hover:bg-red-500/20"
                        >
                          <Trash2 className="w-5 h-5 text-red-400" />
                        </motion.button>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Channel Form Modal */}
      {showChannelModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/90 backdrop-blur-xl z-[60] flex items-center justify-center p-4"
          onClick={() => setShowChannelModal(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="glass-effect rounded-3xl p-8 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white">
                {editingChannel ? "Edit Channel" : "New Channel"}
              </h2>
              <motion.button
                onClick={() => setShowChannelModal(false)}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className="p-2 rounded-xl bg-white/10 hover:bg-white/20"
              >
                <X className="w-5 h-5 text-white" />
              </motion.button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-white/80 mb-2 text-sm font-medium">Channel Name</label>
                <input
                  type="text"
                  value={channelForm.name}
                  onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
                  placeholder="e.g., Gaming Channel, Lifestyle Vlogs"
                />
              </div>

              <div>
                <label className="block text-white/80 mb-2 text-sm font-medium">Google Drive Folder ID</label>
                <input
                  type="text"
                  value={channelForm.drive_folder_id}
                  onChange={(e) => setChannelForm({ ...channelForm, drive_folder_id: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20 font-mono"
                  placeholder="1abc123xyz..."
                />
                <p className="text-white/40 text-xs mt-1">Get this from the Google Drive folder URL</p>
              </div>

              <div>
                <label className="block text-white/80 mb-2 text-sm font-medium">YouTube Account</label>
                <select
                  value={channelForm.youtube_account}
                  onChange={(e) => setChannelForm({ ...channelForm, youtube_account: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl glass-effect text-white focus:outline-none focus:ring-2 focus:ring-white/20 bg-transparent"
                >
                  <option value="account1" className="bg-black">Account 1</option>
                  <option value="account2" className="bg-black">Account 2</option>
                  <option value="account3" className="bg-black">Account 3</option>
                  <option value="account4" className="bg-black">Account 4</option>
                </select>
                <p className="text-white/40 text-xs mt-1">Select which YouTube account to upload to</p>
              </div>

              <div>
                <label className="block text-white/80 mb-2 text-sm font-medium">Categories (comma-separated)</label>
                <input
                  type="text"
                  value={channelForm.categories}
                  onChange={(e) => setChannelForm({ ...channelForm, categories: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
                  placeholder="Gaming, Entertainment, Comedy"
                />
              </div>

              <div>
                <label className="block text-white/80 mb-2 text-sm font-medium">Title Template</label>
                <input
                  type="text"
                  value={channelForm.title_template}
                  onChange={(e) => setChannelForm({ ...channelForm, title_template: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
                  placeholder="{trending_title}"
                />
                <p className="text-white/40 text-xs mt-1">Use {"{trending_title}"}, {"{hashtags}"}, {"{category}"}</p>
              </div>

              <div>
                <label className="block text-white/80 mb-2 text-sm font-medium">Description Template</label>
                <textarea
                  value={channelForm.description_template}
                  onChange={(e) => setChannelForm({ ...channelForm, description_template: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl glass-effect text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20 min-h-[120px]"
                  placeholder="{trending_description}\n\n#shorts"
                />
                <p className="text-white/40 text-xs mt-1">Use {"{trending_description}"}, {"{hashtags}"}</p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <motion.button
                onClick={() => setShowChannelModal(false)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex-1 px-6 py-3 rounded-xl glass-effect hover:bg-white/10 text-white"
              >
                Cancel
              </motion.button>
              <motion.button
                onClick={saveChannel}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex-1 px-6 py-3 rounded-xl bg-white/20 hover:bg-white/30 text-white font-medium flex items-center justify-center gap-2"
              >
                <Save className="w-4 h-4" />
                {editingChannel ? "Update" : "Create"} Channel
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  );
}
