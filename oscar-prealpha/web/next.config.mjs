/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== "production";
const API = process.env.OSCAR_API_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["three"],
  async rewrites() {
    // En prod sur Vercel, /api est servi par la fonction Python (même origine) :
    // aucun rewrite. En dev local, on proxifie vers uvicorn :8000.
    return isDev ? [{ source: "/api/:path*", destination: `${API}/api/:path*` }] : [];
  },
};

export default nextConfig;
