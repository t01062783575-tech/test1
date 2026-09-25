# AI 콘텐츠 워크스페이스

A small AI content workspace demo built with Next.js (App Router), TypeScript,
and React. A signed-in user can type a prompt, submit it, receive a mocked AI
result, and see a history of previous results. Authentication is a simple
local/mock implementation — there is no real backend or user database.

See [`SPEC.md`](./SPEC.md) for the intended behavior of the application.

## Stack

- Next.js 16 (App Router) + TypeScript + React 19
- Mock local authentication (any non-empty username/password combination)
- One API route: `POST /api/generate`, which returns a mocked AI response
- Tailwind CSS v4 for styling
- Vitest + React Testing Library for automated tests

## Getting started

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). You'll be redirected to
`/login` — enter any username and password to sign in.

## Environment variables

Copy `.env.local.example` to `.env.local` before running the app. See that
file for the variables used and their purpose.

## Available scripts

```bash
npm run dev      # start the dev server
npm run build     # production build
npm run start      # run the production build
npm run lint       # eslint
npm test           # run the automated test suite (vitest)
```

## Project structure

- `src/app/page.tsx` — redirects to `/login` or `/workspace` depending on session state
- `src/app/login/page.tsx` + `src/components/LoginForm.tsx` — mock sign-in
- `src/app/workspace/page.tsx` + `src/app/workspace/workspace-client.tsx` — main authenticated workspace
- `src/components/SubmissionForm.tsx` — prompt input and submission
- `src/components/ResultsList.tsx` — history of previous results
- `src/components/StatsBar.tsx` — small usage stats panel
- `src/app/api/generate/route.ts` — mocked AI generation endpoint
- `src/lib/mockAi.ts` — pure function producing mocked AI output
- `src/middleware.ts` — route protection for `/login` and `/workspace`
- `tests/` — automated tests (Vitest + React Testing Library)
