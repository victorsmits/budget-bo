const fs = require('fs')
const path = require('path')

/** @type {(config: import('next').NextConfig) => import('next').NextConfig} */
const identity = (config) => config

const hasNextPwa = fs.existsSync(path.join(__dirname, 'node_modules', 'next-pwa'))
const hasNextIntl = fs.existsSync(path.join(__dirname, 'node_modules', 'next-intl'))

const withPWA = hasNextPwa
  ? require('next-pwa')({
      dest: 'public',
      disable: process.env.NODE_ENV === 'development',
      register: true,
      skipWaiting: true,
    })
  : identity

const withNextIntl = hasNextIntl ? require('next-intl/plugin')('./i18n/request.ts') : identity

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    if (process.env.NODE_ENV === 'production') {
      return []
    }

    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
      },
    ],
  },
}

module.exports = withPWA(withNextIntl(nextConfig))
