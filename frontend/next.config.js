/** @type {import('next').NextConfig} */
// BACKEND_URL: for local testing, this stays the docker-compose network
// hostname (http://backend:8000). For real deployment, Cloud Run services
// don't share an internal network the way docker-compose containers do —
// each gets its own independent URL — so this needs to be set to the
// backend's real Cloud Run URL as an environment variable at deploy time.
const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";

module.exports = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
    ];
  },
};
