import type { GenerationResult } from "@/lib/types";

export default function ResultsList({ results }: { results: GenerationResult[] }) {
  if (results.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
        아직 생성된 결과가 없어요. 위에서 내용을 입력하고 제출해보세요.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {results.map((result) => (
        <li key={result.id} className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-400">
            {new Date(result.createdAt).toLocaleString("ko-KR")}
          </p>
          <p className="mt-2 text-sm font-medium text-slate-700">
            입력: {result.input}
          </p>
          <p className="mt-1 text-sm text-slate-900">결과: {result.output}</p>
        </li>
      ))}
    </ul>
  );
}
