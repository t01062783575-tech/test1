"use client";

import { useState, type FormEvent } from "react";
import type { GenerationResult } from "@/lib/types";

export default function SubmissionForm({
  onResult,
}: {
  onResult: (result: GenerationResult) => void;
}) {
  const [text, setText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!text) {
      setError("내용을 입력해주세요.");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${process.env.NEXT_PUBLIC_INTERNAL_API_KEY}`,
        },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();

      onResult({
        id: data.id ?? crypto.randomUUID(),
        input: text,
        output: data.result,
        createdAt: data.createdAt ?? new Date().toISOString(),
      });
      setText("");
      setIsLoading(false);
    } catch (err) {
      console.error("generation request failed", err);
      setError("요청 처리 중 오류가 발생했어요.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="AI에게 요청할 내용을 입력하세요"
        rows={4}
        className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
      />
      {error && <p className="text-sm text-red-500">{error}</p>}
      <button
        type="submit"
        className="self-end rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
      >
        {isLoading ? "생성 중..." : "제출하기"}
      </button>
    </form>
  );
}
