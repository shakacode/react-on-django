import React from "react";
import { renderToString } from "react-dom/server";

import MetadataMessage from "./MetadataMessage.client";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export default function renderMetadataMessage(props, _railsContext) {
  const { helloWorldData } = props;
  const name = helloWorldData?.name ?? "World";
  const componentHtml = renderToString(<MetadataMessage {...props} />);

  return {
    renderedHtml: {
      componentHtml,
      title: `<title>${escapeHtml(name)} | Metadata Example</title>`,
    },
  };
}
