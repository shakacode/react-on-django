const path = require("path");
const { PassThrough } = require("stream");

const { reactOnRailsProNodeRenderer } = require("react-on-rails-pro-node-renderer");

reactOnRailsProNodeRenderer({
  serverBundleCachePath: path.resolve(__dirname, "../tmp/node-renderer-bundles"),
  port: Number(process.env.RENDERER_PORT || 3800),
  logLevel: process.env.RENDERER_LOG_LEVEL || "info",
  password:
    process.env.RENDERER_PASSWORD ||
    process.env.REACT_ON_DJANGO_RENDERER_PASSWORD ||
    process.env.REACT_ON_DJANGO_RENDERING_SERVER_PASSWORD ||
    "react-on-django-example",
  supportModules: true,
  additionalContext: { URL, AbortController, PassThrough },
  stubTimers: false,
  replayServerAsyncOperationLogs: true,
  workersCount: 0,
});
