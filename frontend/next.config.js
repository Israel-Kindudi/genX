/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack(config, { dev }) {
    if (!dev) {
      config.plugins.push(
        new (require("webpack").NormalModuleReplacementPlugin)(
          /accountDataProviderDevelopment$/,
          require("path").resolve(__dirname, "lib/accountDataProviderProductionStub.ts")
        )
      );
    }
    return config;
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
  async headers() {
    const privateHeaders = [
      { key: "X-Robots-Tag", value: "noindex, nofollow, noarchive" },
      {
        key: "Cache-Control",
        value: "private, no-store, max-age=0, must-revalidate",
      },
    ];

    return [
      { source: "/dashboard/:path*", headers: privateHeaders },
      { source: "/login", headers: privateHeaders },
      { source: "/register", headers: privateHeaders },
      { source: "/checkout/:path*", headers: privateHeaders },
      { source: "/api/:path*", headers: privateHeaders },
    ];
  },
};

module.exports = nextConfig;