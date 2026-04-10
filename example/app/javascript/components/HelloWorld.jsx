import React, { useState } from "react";

export default function HelloWorld(props) {
  const { helloWorldData } = props;
  const [name, setName] = useState(helloWorldData?.name ?? "World");
  const note = helloWorldData?.note ?? "";

  return (
    <div className="hello-world">
      <h3 className="hello-world__title">Hello, {name}!</h3>
      <p className="hello-world__controls">
        Say hello to:
        <input
          className="hello-world__input"
          onChange={(event) => setName(event.target.value)}
          type="text"
          value={name}
        />
      </p>
      {note ? <p className="hello-world__note">{note}</p> : null}
    </div>
  );
}
