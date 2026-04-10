import { expect, test } from "@playwright/test";

test("client rendering and html options behave correctly", async ({ page }) => {
  await page.goto("/client_side_hello_world/");
  await expect(page.locator(".hello-world__title")).toContainText("Mr. Client Side Rendering");
  await page.locator(".hello-world__input").fill("Taylor");
  await expect(page.locator(".hello-world__title")).toContainText("Taylor");
  await expect(page.locator(".hello-world__note")).toContainText(
    '<script>window.alert("xss-from-props")</script>',
  );

  await page.goto("/client_side_hello_world_with_options/");
  const container = page.locator("#my-hello-world-id");
  await expect(container).toHaveAttribute("class", "my-hello-world-class");
  await expect(container).toHaveAttribute("data-x", "1");
  await expect(container).toHaveAttribute("data-y", "2");
});

test("shared-store example waits for deferred store hydration", async ({ page }) => {
  await page.goto("/client_side_hello_world_shared_store/");

  await expect(page.locator(".hello-world__title")).toContainText(
    "Hello from store, Mr. Client Side Rendering!",
  );
  await expect(
    page.locator('[data-js-react-on-rails-store="helloWorldStore"]'),
  ).toHaveCount(1);
});

test("metadata and server_render_js examples expose server-only helper output", async ({ page }) => {
  await page.goto("/server_render_js_example/");
  await expect(page.getByTestId("hello-string-output")).toHaveText("Hello from server_render_js");

  await page.goto("/metadata_example/");
  await expect(page).toHaveTitle("Mr. Client Side Rendering | Metadata Example");
  await expect(page.getByTestId("metadata-message")).toBeVisible();
  await expect(page.locator(".hello-world__title")).toContainText("Metadata for Mr. Client Side Rendering");
});

test("ssr and streaming example routes render the demo pages", async ({ page }) => {
  await page.goto("/server_side_hello_world/");
  await expect(page.getByRole("heading", { name: /server-side rendering/i })).toBeVisible();
  await expect(page.locator(".hello-world__title")).toContainText("Mr. Client Side Rendering");

  await page.goto("/server_side_hello_world_shared_store/");
  await expect(page.getByRole("heading", { name: /server-side shared-store registration/i })).toBeVisible();
  await expect(page.locator(".hello-world__title").first()).toContainText(
    "Hello from store, Mr. Client Side Rendering!",
  );

  await page.goto("/streaming_hello_world/");
  await expect(page.getByRole("heading", { name: /streaming response example/i })).toBeVisible();
  await expect(page.locator(".hello-world__title")).toContainText("Mr. Client Side Rendering");
});

test("rsc example hydrates from the embedded payload and refetches on prop changes", async ({
  page,
}) => {
  const rscRequests = [];
  page.on("request", (request) => {
    if (request.url().includes("/react_on_django/rsc/")) {
      rscRequests.push(request.url());
    }
  });

  await page.goto("/rsc_hello_world/");
  await expect(page.getByRole("heading", { name: /RSC-enabled streaming example/i })).toBeVisible();
  await expect(page.getByTestId("rsc-card")).toBeVisible();
  await expect(page.getByTestId("rsc-note")).toHaveText(
    "The initial payload was embedded during server rendering.",
  );
  await expect(page.getByText("Hello from RSC, RSC from Django!")).toBeVisible();
  const initialRequestCount = rscRequests.length;

  const fetchPromise = page.waitForRequest((request) =>
    request.url().includes("/react_on_django/rsc/RscHelloWorld"),
  );
  await page.getByRole("button", { name: "Refresh RSC Payload" }).click();
  await fetchPromise;
  await expect.poll(() => rscRequests.length).toBeGreaterThan(initialRequestCount);

  await expect(page.getByTestId("rsc-note")).toHaveText(
    "The initial payload was embedded during server rendering. (client refresh)",
  );
});
