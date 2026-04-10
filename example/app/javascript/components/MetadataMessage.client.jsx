import React from "react";

export default function MetadataMessage(props) {
  const { helloWorldData } = props;
  const name = helloWorldData?.name ?? "World";
  const note = helloWorldData?.note ?? "";

  return (
    <section className="hello-world" data-testid="metadata-message">
      <h3 className="hello-world__title">Metadata for {name}</h3>
      <p className="hello-world__note">{note}</p>
    </section>
  );
}
