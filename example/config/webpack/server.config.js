const path = require("path");
const webpack = require("webpack");
const { RSCWebpackPlugin } = require("react-on-rails-rsc/WebpackPlugin");

const {
  exampleDir,
  packsDir,
  publicPath,
  webpackMode,
  reactAliases,
  makeBabelRule,
} = require("./shared");

module.exports = {
  mode: webpackMode,
  target: "node",
  entry: path.resolve(exampleDir, "app/javascript/packs/server-bundle.jsx"),
  output: {
    path: packsDir,
    publicPath,
    filename: "server-bundle.js",
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
    alias: reactAliases,
  },
  module: {
    rules: [makeBabelRule("node")],
  },
  plugins: [
    new webpack.optimize.LimitChunkCountPlugin({
      maxChunks: 1,
    }),
    new RSCWebpackPlugin({
      isServer: true,
      clientReferences: {
        directory: path.resolve(exampleDir, "app/javascript/components"),
        include: /\.[jt]sx?$/,
      },
    }),
  ],
};
