"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import LogoutButton from "@/components/LogoutButton";
import StatsBar from "@/components/StatsBar";
import SubmissionForm from "@/components/SubmissionForm";
import ResultsList from "@/components/ResultsList";
import type { GenerationResult } from "@/lib/types";

export default function WorkspaceClient() {
  const router = useRouter();
  const [user] = useState<string | null>(() =>
    typeof window === "undefined" ? null : localStorage.getItem("workspace_user")
  );
  const [results, setResults] = useState<GenerationResult[]>([]);

  useEffect(() => {
    if (!user) {
      router.push("/login");
    }
  }, [user, router]);

  if (!user) {
    return <p className="p-8 text-sm text-slate-500">불러오는 중...</p>;
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-10">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            AI 콘텐츠 워크스페이스
          </h1>
          <p className="text-sm text-slate-500">{user}님, 환영합니다.</p>
        </div>
        <LogoutButton />
      </header>

      <StatsBar resultCount={results.length} />

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-slate-700">새 콘텐츠 생성</h2>
        <SubmissionForm onResult={(result) => setResults((prev) => [result, ...prev])} />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-slate-700">이전 결과</h2>
        <ResultsList results={results} />
      </section>
    </main>
  );
}
