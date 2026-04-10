import { spawn } from "node:child_process";
import { mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { resolveAssetOutput, writeExampleManifest } from "./write_example_manifest.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const exampleDir = path.resolve(__dirname, "..");
const configDir = path.join(exampleDir, "config", "webpack");
const mode = process.argv[2] ?? "development";
const { packsDir } = resolveAssetOutput({ exampleDir, mode });

function run(command, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: exampleDir,
      env,
      stdio: "inherit",
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${command} ${args.join(" ")} exited with code ${code ?? "unknown"}`));
    });
  });
}

await rm(packsDir, { force: true, recursive: true });
await mkdir(packsDir, { recursive: true });

for (const configName of [
  "client.config.js",
  "server.config.js",
  "rsc.config.js",
]) {
  await run(
    "npx",
    ["webpack", "--config", path.join(configDir, configName)],
    {
      ...process.env,
      NODE_ENV: mode,
      HMR: "false",
    },
  );
}

await writeExampleManifest({ exampleDir, mode, hmr: false });
