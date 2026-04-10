'use client';

import React, { Suspense, useState } from "react";

import RSCRoute from "react-on-rails-pro/RSCRoute";

export default function RscAppShell(initialProps) {
  const [rscProps, setRscProps] = useState(initialProps);

  return (
    <section className="rsc-demo">
      <div className="rsc-demo__controls">
        <button
          className="rsc-demo__button"
          onClick={() =>
            setRscProps((currentProps) => ({
              ...currentProps,
              note: `${initialProps.note} (client refresh)`,
            }))
          }
          type="button"
        >
          Refresh RSC Payload
        </button>
      </div>
      <Suspense fallback={<p data-testid="rsc-fallback">Loading RSC payload...</p>}>
        <RSCRoute componentName="RscHelloWorld" componentProps={rscProps} />
      </Suspense>
    </section>
  );
}
