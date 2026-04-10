import { expect, test } from "@playwright/test";

test("the rsc payload endpoint returns the NDJSON RSC payload", async ({ request, baseURL }) => {
  const props = {
    name: "Payload Ada",
    note: '`quoted` ${template} <script>alert("xss")</script>',
  };
  const response = await request.get(
    `${baseURL}/react_on_django/rsc/RscHelloWorld/?props=${encodeURIComponent(JSON.stringify(props))}`,
  );

  expect(response.ok()).toBeTruthy();
  expect(response.headers()["content-type"]).toContain("application/x-ndjson");
  const body = await response.text();
  const chunks = body
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));

  expect(chunks[0].hasErrors).toBeFalsy();
  expect(chunks[0].html).toContain("Payload Ada");
  expect(chunks[0].html).toContain("template");
  expect(chunks[0].html).toContain("Hello from RSC");
});
