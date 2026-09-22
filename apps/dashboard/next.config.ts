import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Runtime image copie .next/standalone + .next/static (voir apps/dashboard/Dockerfile) :
  // évite d'embarquer le CLI npm (et ses dépendances vulnérables, cf. scan Trivy) dans l'image finale.
  output: "standalone",
};

export default nextConfig;
