프리랜서·1인사업자를 위한 경비 자동정리 SaaS 사전예약 랜딩페이지입니다.

## Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Supabase 설정

이메일 사전예약은 Supabase 테이블에 저장됩니다.

1. Supabase 프로젝트에서 아래 SQL로 테이블과 RLS 정책을 만드세요.

   ```sql
   create table freelancer_waitlist (
     id uuid primary key default gen_random_uuid(),
     email text not null unique,
     created_at timestamptz not null default now()
   );

   alter table freelancer_waitlist enable row level security;

   create policy "Allow public insert"
     on freelancer_waitlist
     for insert
     to anon
     with check (true);
   ```

2. `.env.local.example`을 복사해 `.env.local`을 만들고 값을 채워주세요.

   ```bash
   cp .env.local.example .env.local
   ```

   - `SUPABASE_URL`: Supabase 프로젝트 설정 → API에서 확인
   - `SUPABASE_ANON_KEY`: 동일 화면의 anon/public key

3. 개발 서버를 재시작하면 하단/상단 폼에서 등록한 이메일이 `freelancer_waitlist` 테이블에 저장됩니다.

## 프로젝트 구조

- `src/app/page.tsx` — 랜딩페이지 (히어로, 문제 공감, 기능 3종, 하단 CTA)
- `src/app/actions.ts` — 이메일 등록 Server Action (Supabase insert)
- `src/components/EmailSignupForm.tsx` — 재사용 가능한 이메일 등록 폼
- `src/lib/supabase.ts` — Supabase 서버 클라이언트

## Deploy

Vercel 등에 배포 시 `SUPABASE_URL`, `SUPABASE_ANON_KEY` 환경 변수를 설정해주세요.
