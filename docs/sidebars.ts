import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebars: SidebarsConfig = {
  docs: [
    "introduction",
    {
      type: "category",
      label: "Getting Started",
      items: [
        "getting-started/installation",
        "getting-started/quick-start",
        "getting-started/create-react-on-django-app",
      ],
    },
    {
      type: "category",
      label: "Guides",
      items: [
        "guides/client-rendering",
        "guides/helper-apis",
        "guides/server-rendering",
        "guides/streaming-ssr",
        "guides/rsc",
        "guides/configuration",
        "guides/testing-and-operations",
        "guides/licensing",
      ],
    },
  ],
};

export default sidebars;
