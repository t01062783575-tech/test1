export default function StatsBar({ resultCount }: { resultCount: number }) {
  return (
    <div className="flex gap-4">
      <div className="w-[160px] shrink-0 rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-xs text-slate-500">총 생성 수</p>
        <p className="mt-1 text-2xl font-bold text-slate-900">{resultCount}</p>
      </div>
      <div className="w-[160px] shrink-0 rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-xs text-slate-500">오늘 사용량</p>
        <p className="mt-1 text-2xl font-bold text-slate-900">{resultCount}</p>
      </div>
      <div className="w-[160px] shrink-0 rounded-xl border border-slate-200 bg-white p-4">
        <p className="text-xs text-slate-500">플랜</p>
        <p className="mt-1 text-2xl font-bold text-slate-900">Free</p>
      </div>
    </div>
  );
}
