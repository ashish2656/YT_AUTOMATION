import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  
  // Exclude python directory from webpack watch
  webpack: (config) => {
    config.watchOptions = {
      ...config.watchOptions,
      ignored: ['**/python/**', '**/node_modules/**'],
    };
    return config;
  },
};

export default nextConfig;
