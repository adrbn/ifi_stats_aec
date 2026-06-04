/** @type {import('next').NextConfig} */
const API = process.env.OSCAR_API_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["three"],
  async rewrites() {
    // Proxy /api/* to the FastAPI backend so the browser stays same-origin.
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
