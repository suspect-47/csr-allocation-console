/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone", // slim Docker image (spec §7)
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
