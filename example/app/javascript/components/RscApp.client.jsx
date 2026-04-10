'use client';

import React from "react";

import wrapServerComponentRenderer from "react-on-rails-pro/wrapServerComponentRenderer/client";

import RscAppShell from "./RscAppShell.client";

function RscApp(props) {
  return <RscAppShell {...props} />;
}

export default wrapServerComponentRenderer(RscApp);
