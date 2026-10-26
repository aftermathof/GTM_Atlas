# Inline Citations Implementation Plan

> Execute inline with test-driven-development and verification-before-completion.

**Goal:** Render numbered source links beside cited sentences and share numbering with the final file list.

**Architecture:** A small frontend helper groups citation chunks by document, builds internal chapter URLs and exposes a Marked inline extension. Markdown and ChatPanel share it. Backend generation guidance requests sentence-end markers without changing the validated response schema.

**Tech Stack:** Vue 3, TypeScript, Marked, DOMPurify, node:test, pytest.

## Constraints

- Use existing dependencies and stored citation metadata.
- Preserve unrelated glossary edits.
- One number per file per answer; keep existing citation order.
- Do not infer missing citation locations.

## Steps

- [x] Add `apps/web/scripts/ai-citations.test.mjs`: use actual Marked parsing to verify grouped numbering, sentence positions, chapter URLs, code/link preservation, unknown markers and injection protection. Run `node --test apps/web/scripts/ai-citations.test.mjs` and confirm failure before implementation.
- [x] Add `apps/web/src/aiCitations.ts` exporting `citationHref`, `citationSources` and `citationExtension`; preserve chunk-specific chapter links while grouping list entries by document.
- [x] Update `Markdown.vue` to consume optional citation metadata and parse AI markers through the extension; style compact raised links and route their clicks internally.
- [x] Update `ChatPanel.vue` to supply citation metadata and display the deduplicated numbered source list.
- [x] Add a backend test for the generation instruction and verified multi-chunk citations; confirm failure, then update the prompt in `packages/learning/graph.py` to require sentence-end source markers for all stored files.
- [x] Run citation and AI-text frontend tests, related chat backend tests, Vue type checking and Vite compilation. Inspect diff and mark this plan complete after checks pass.

## Verification results

- Citation and AI text frontend checks: 7 passed.
- Chat, private-note and stored-reference backend checks: 11 passed (local socket tests run outside the Windows sandbox).
- Vue type checking and Vite production build: passed.
- Git diff whitespace check: passed.
