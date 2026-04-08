# Napkin Runbook

## Curation Rules
1. **[2026-04-07] Keep this file high signal**
   Do instead: re-prioritize on every read, keep recurring guidance only, and cap each category at 10 items.

## Execution & Validation (Highest Priority)
1. **[2026-04-07] Validate the smallest complete slice first**
   Do instead: finish packaging, config, rendering, and tests for the client-only path before layering SSR or generators.

## Domain Behavior Guardrails
1. **[2026-04-07] Preserve the shared React on Rails DOM contract**
   Do instead: keep `js-react-on-rails-context`, `js-react-on-rails-component`, `data-component-name`, `data-dom-id`, and RailsContext-compatible keys until the shared JS runtime is intentionally changed.
2. **[2026-04-07] Keep bundler integration behind a seam**
   Do instead: make `react-on-django` core rendering work without importing `django-rspack`, then plug asset loading in through configuration or an adapter.

## Shell & Command Reliability
1. **[2026-04-07] New repos can fail fast on missing tooling**
   Do instead: check local Python and package availability before choosing packaging and test commands.

## User Directives
1. **[2026-04-07] Complete the cleanup loop for review-style work**
   Do instead: inspect, fix, test, clean incidental artifacts, and only then ask for user attention unless a real blocker appears.
