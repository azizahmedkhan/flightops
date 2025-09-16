/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: []
  },
  env: {
    GATEWAY_URL: process.env.GATEWAY_URL || 'http://localhost:8080',
  }
}

module.exports = nextConfig
