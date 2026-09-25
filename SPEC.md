# AI 콘텐츠 워크스페이스 — Intended Behavior

This document describes how the application is intended to behave. It is the
functional baseline against which the implementation should be evaluated.

## 1. Authentication

- Unauthenticated visitors are sent to `/login`.
- The login form accepts any non-empty username and password combination
  (this is mock authentication — there is no real user database or password
  check).
- After a successful login, the user is taken to `/workspace` and stays
  signed in across page reloads within the same browser session.
- Visiting `/login` while already signed in should send the user straight to
  `/workspace`.
- Visiting `/workspace` while signed out should send the user to `/login`.
- Logging out should fully end the session: the user should land on `/login`
  and stay there, with no way to reach `/workspace` without signing in again.

## 2. Submitting content

- The workspace has a single text field and a "제출하기" (Submit) button.
- Submitting is only meaningful for real, non-blank text. Blank or
  whitespace-only submissions should be rejected with a clear inline message
  before any request is made.
- While a request is in flight, the UI should clearly indicate a loading
  state and prevent the same submission from being sent twice (e.g. from a
  double click or repeated Enter presses).
- On success, a new result should appear at the top of the "이전 결과"
  (previous results) list, containing the original input, the generated
  output, and a timestamp.
- On failure (network error or server error), the loading state should
  clear, and the user should see a clear, user-facing error message
  explaining that the request failed and inviting them to retry. A failed
  request should never silently produce a blank or malformed entry in the
  results list, and should never leave the UI stuck in a loading state.

## 3. Previous results

- All results generated during the current session are listed in
  reverse-chronological order (newest first).
- Each entry shows the original input, the generated output, and when it was
  created.
- An empty state is shown when no results exist yet.

## 4. Responsive layout

- All pages (login and workspace) are expected to render correctly, without
  horizontal scrolling or clipped content, at common mobile widths (e.g. an
  iPhone SE at 375px wide) as well as on tablet and desktop widths.

## 5. Configuration

- The app reads configuration from environment variables (see
  `.env.local.example`). Any value that is genuinely sensitive (API keys,
  credentials) must never be readable from the browser — it should only ever
  be used in server-side code (Server Components, Route Handlers, Server
  Actions), never bundled into client-side JavaScript.
