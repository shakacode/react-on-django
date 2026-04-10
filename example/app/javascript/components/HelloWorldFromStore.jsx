import React from "react";
import RuntimeBridge from "react-on-rails-pro/client";

export default function HelloWorldFromStore({ storeName = "helloWorldStore" }) {
  const store = RuntimeBridge.getStore(storeName);
  const storeState = store?.getState?.() ?? {};
  const name = storeState.helloWorldData?.name ?? "World";

  return (
    <div className="hello-world">
      <h3 className="hello-world__title">Hello from store, {name}!</h3>
      <p className="hello-world__note">
        This component waits for a deferred store hydration tag before it renders.
      </p>
    </div>
  );
}
