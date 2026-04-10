import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export function resolveAssetOutput({
  exampleDir = path.resolve(__dirname, ".."),
  mode = "development",
} = {}) {
  const outputDirName = mode === "test" ? "packs-test" : "packs";
  return {
    outputDirName,
    packsDir: path.join(exampleDir, "public", outputDirName),
    publicPath: `/${outputDirName}/`,
  };
}

export async function writeExampleManifest({
  exampleDir = path.resolve(__dirname, ".."),
  mode = "development",
  hmr = false,
} = {}) {
  const { outputDirName, packsDir, publicPath } = resolveAssetOutput({ exampleDir, mode });
  await mkdir(packsDir, { recursive: true });

  const manifest = {
    "application.js": `${publicPath}application.js`,
    "server-bundle.js": `${publicPath}server-bundle.js`,
    "rsc-bundle.js": `${publicPath}rsc-bundle.js`,
    "react-client-manifest.json": `${publicPath}react-client-manifest.json`,
    "react-server-client-manifest.json": `${publicPath}react-server-client-manifest.json`,
    entrypoints: {
      application: {
        assets: {
          js: [`${publicPath}application.js`],
          css: hmr ? [] : [`${publicPath}application.css`],
        },
      },
    },
    metadata: {
      mode,
      hmr,
      outputDirName,
    },
  };

  if (!hmr) {
    manifest["application.css"] = `${publicPath}application.css`;
  }

  await writeFile(
    path.join(packsDir, "manifest.json"),
    `${JSON.stringify(manifest, null, 2)}\n`,
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const mode = process.argv[2] ?? "development";
  const hmr = process.argv.includes("--hmr");
  await writeExampleManifest({ mode, hmr });
}
