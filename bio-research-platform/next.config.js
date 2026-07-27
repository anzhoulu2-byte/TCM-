/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
  },
  // API 代理 — 将 /api/* 转发到后端，避免跨域问题
  async rewrites() {
    return [
      {
        source: "/api-proxy/:path*",
        destination: "http://localhost:8510/api/:path*",
      },
    ]
  },
  // 环境变量
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8510",
  },
}

module.exports = nextConfig
