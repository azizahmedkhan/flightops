/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: []
  },
  env: {
    GATEWAY_URL: process.env.GATEWAY_URL || 'http://localhost:8080',
  },
  // Production optimizations
  compress: true,
  poweredByHeader: false,
  generateEtags: false,
  // Disable React StrictMode in production to prevent double rendering
  reactStrictMode: process.env.NODE_ENV !== 'production',
}

module.exports = nextConfig
