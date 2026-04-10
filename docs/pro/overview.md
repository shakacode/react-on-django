# Pro Overview

The long-term goal is feature parity with the Pro surface from the ShakaCode
React on Rails ecosystem, translated into Django-idiomatic APIs.

That roadmap includes:

- streaming SSR helpers and controller concerns
- cached render helpers
- richer RSC helpers and payload helpers
- async render helpers
- router and metadata demos
- a broader dummy app and Playwright suite

The current package already ships the first meaningful Pro slice:

- streamed HTML responses
- NDJSON RSC payload responses
- renderer retry and bundle upload behavior
- a live example app that exercises client, SSR, streaming, and RSC paths
