import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pure static files on Netlify's CDN: no server functions, so no cold starts (TRD §2).
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
