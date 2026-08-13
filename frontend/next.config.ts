import type { NextConfig } from "next";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";

const PUBLIC_ENV_KEYS = [
  "NEXT_PUBLIC_LOCK_LLM_MODEL",
  "NEXT_PUBLIC_ENABLE_LLM_CONSOLE",
] as const;

function readRootPublicEnv(): Record<string, string> {
  const values: Record<string, string> = {};
  const cwd = process.cwd();
  const envPaths = [resolve(cwd, ".env")];
  if (existsSync(resolve(cwd, "..", "frontend", "package.json"))) {
    envPaths.push(resolve(cwd, "..", ".env"));
  }

  for (const envPath of envPaths) {
    if (!existsSync(envPath)) {
      continue;
    }
    for (const rawLine of readFileSync(envPath, "utf-8").split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) {
        continue;
      }
      const separatorIndex = line.indexOf("=");
      if (separatorIndex < 0) {
        continue;
      }
      const key = line.slice(0, separatorIndex).trim();
      if (!PUBLIC_ENV_KEYS.includes(key as (typeof PUBLIC_ENV_KEYS)[number])) {
        continue;
      }
      const rawValue = line.slice(separatorIndex + 1).trim();
      values[key] = rawValue.replace(/^(['"])(.*)\1$/, "$2");
    }
  }
  return values;
}

const rootPublicEnv = readRootPublicEnv();
const publicEnv = Object.fromEntries(
  PUBLIC_ENV_KEYS.map((key) => [key, process.env[key] ?? rootPublicEnv[key] ?? ""])
);

const nextConfig: NextConfig = {
  env: publicEnv,
  // Emit a self-contained server bundle (.next/standalone) for a slim Docker image.
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
