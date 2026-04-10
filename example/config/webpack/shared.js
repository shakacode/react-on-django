const path = require("path");

const exampleDir = path.resolve(__dirname, "..", "..");
const nodeModulesDir = path.resolve(exampleDir, "node_modules");
const mode = process.env.NODE_ENV || "development";
const webpackMode = mode === "production" ? "production" : "development";
const isHmr = process.env.HMR === "true";
const outputDirName = process.env.RSPACK_OUTPUT_DIR || (mode === "test" ? "packs-test" : "packs");
const packsDir = path.resolve(exampleDir, "public", outputDirName);
const publicPath = `/${outputDirName}/`;

const reactAliases = {
  "react$": path.resolve(nodeModulesDir, "react"),
  "react/jsx-runtime$": path.resolve(nodeModulesDir, "react", "jsx-runtime"),
  "react/jsx-dev-runtime$": path.resolve(nodeModulesDir, "react", "jsx-dev-runtime"),
  "react-dom$": path.resolve(nodeModulesDir, "react-dom"),
  "react-dom/client$": path.resolve(nodeModulesDir, "react-dom", "client"),
  "react-dom/server$": path.resolve(nodeModulesDir, "react-dom", "server"),
};

function makeBabelRule(target) {
  return {
    test: /\.[jt]sx?$/,
    exclude: /node_modules/,
    use: {
      loader: "babel-loader",
      options: {
        presets: [
          [
            "@babel/preset-env",
            target === "node"
              ? { targets: { node: "current" } }
              : { targets: "defaults" },
          ],
          ["@babel/preset-react", { runtime: "automatic" }],
        ],
      },
    },
  };
}

module.exports = {
  exampleDir,
  packsDir,
  publicPath,
  mode,
  webpackMode,
  isHmr,
  reactAliases,
  makeBabelRule,
};
