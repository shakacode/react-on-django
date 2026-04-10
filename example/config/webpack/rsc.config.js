const path = require("path");
const webpack = require("webpack");

const {
  exampleDir,
  packsDir,
  publicPath,
  webpackMode,
  makeBabelRule,
} = require("./shared");

const nodeModulesDir = path.resolve(exampleDir, "node_modules");

module.exports = {
  mode: webpackMode,
  target: "node",
  entry: path.resolve(exampleDir, "app/javascript/packs/rsc-bundle.jsx"),
  output: {
    path: packsDir,
    publicPath,
    filename: "rsc-bundle.js",
    library: {
      type: "commonjs2",
    },
    clean: false,
  },
  devtool: "eval",
  optimization: {
    minimize: false,
    splitChunks: false,
    runtimeChunk: false,
  },
  resolve: {
    extensions: [".js", ".jsx"],
    conditionNames: ["react-server", "..."],
    alias: {
      "react$": path.resolve(nodeModulesDir, "react", "react.react-server.js"),
      "react/jsx-runtime$": path.resolve(
        nodeModulesDir,
        "react",
        "jsx-runtime.react-server.js",
      ),
      "react/jsx-dev-runtime$": path.resolve(
        nodeModulesDir,
        "react",
        "jsx-dev-runtime.react-server.js",
      ),
      "react-dom/server$": false,
    },
  },
  module: {
    rules: [makeBabelRule("node")],
  },
  plugins: [
    new webpack.optimize.LimitChunkCountPlugin({
      maxChunks: 1,
    }),
  ],
};
