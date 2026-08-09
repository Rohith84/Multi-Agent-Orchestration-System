import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/workflows",
        destination: "/app/workflows",
        permanent: true,
      },
      {
        source: "/workflow-builder",
        destination: "/app/workflow-builder",
        permanent: true,
      },
      {
        source: "/chat",
        destination: "/app/chat",
        permanent: true,
      },
      {
        source: "/knowledge",
        destination: "/app/knowledge",
        permanent: true,
      },
      {
        source: "/tools",
        destination: "/app/tools",
        permanent: true,
      },
      {
        source: "/workspace",
        destination: "/app/workspace",
        permanent: true,
      },
      {
        source: "/artifacts",
        destination: "/app/artifacts",
        permanent: true,
      },
      {
        source: "/analytics",
        destination: "/app/analytics",
        permanent: true,
      }
    ];
  },
};

export default nextConfig;
