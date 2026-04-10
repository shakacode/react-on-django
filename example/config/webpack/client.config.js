const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { RSCWebpackPlugin } = require("react-on-rails-rsc/WebpackPlugin");

const {
  exampleDir,
  packsDir,
  publicPath,
  isHmr,
  mode,
  webpackMode,
  reactAliases,
  makeBabelRule,
} = require("./shared");

const emitCssFile = !isHmr;

module.exports = {
  mode: webpackMode,
  entry: path.resolve(exampleDir, "app/javascript/packs/application.jsx"),
  output: {
    path: packsDir,
    publicPath,
    filename: "application.js",
    clean: false,
  },
  devtool: mode === "production" ? "source-map" : "eval-cheap-module-source-map",
  resolve: {
    extensions: [".js", ".jsx"],
    alias: reactAliases,
  },
  module: {
    rules: [
      makeBabelRule("web"),
      {
        test: /\.css$/,
        use: [
          emitCssFile ? MiniCssExtractPlugin.loader : "style-loader",
          "css-loader",
        ],
      },
    ],
  },
  plugins: emitCssFile
    ? [
        new MiniCssExtractPlugin({
          filename: "application.css",
        }),
        new RSCWebpackPlugin({
          isServer: false,
          clientReferences: {
            directory: path.resolve(exampleDir, "app/javascript/components"),
            include: /\.[jt]sx?$/,
          },
        }),
      ]
    : [
        new RSCWebpackPlugin({
          isServer: false,
          clientReferences: {
            directory: path.resolve(exampleDir, "app/javascript/components"),
            include: /\.[jt]sx?$/,
          },
        }),
      ],
  devServer: {
    host: "127.0.0.1",
    port: Number(process.env.RSPACK_DEV_SERVER_PORT || 3035),
    compress: false,
    hot: true,
    liveReload: true,
    allowedHosts: "all",
    headers: {
      "Access-Control-Allow-Origin": "*",
    },
    devMiddleware: {
      writeToDisk: true,
    },
    static: false,
  },
};
