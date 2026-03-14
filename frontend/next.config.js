/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // En production, PAS de rewrite (géré par Nginx)
    // En développement, rewrite vers localhost:8000
    if (process.env.NODE_ENV === 'production') {
      return []  // Pas de rewrite en production
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

module.exports = nextConfig
