import React from "react";

export default function RscHelloWorld({ name, note }) {
  return (
    <article className="rsc-card" data-testid="rsc-card">
      <p className="shell__eyebrow">React Server Component</p>
      <h3 className="hello-world__title">Hello from RSC, {name}!</h3>
      <p className="hello-world__note" data-testid="rsc-note">
        {note}
      </p>
      <pre className="rsc-card__props" data-testid="rsc-props">
        {JSON.stringify({ name, note }, null, 2)}
      </pre>
    </article>
  );
}
