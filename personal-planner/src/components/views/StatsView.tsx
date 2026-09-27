"use client";

import { WEEKDAYS, addDays, fromKey, rangeKeys, toKey } from "@/lib/date";
import { useStore } from "@/lib/store";
import { useApp } from "../AppContext";

/** 날짜별로 완료한 할일 수 (반복 할일은 회차마다 1개) */
function completedByDay(items: ReturnType<typeof useStore>["data"]["items"]): Map<string, number> {
  const map = new Map<string, number>();
  const add = (d: string) => map.set(d, (map.get(d) ?? 0) + 1);
  for (const i of items) {
    if (i.kind !== "task") continue;
    if (i.repeat.freq === "none") {
      if (i.done && i.completedAt) add(toKey(new Date(i.completedAt)));
    } else {
      i.doneDates.forEach(add);
    }
  }
  return map;
}

export function StatsView() {
  const { data } = useStore();
  const { today } = useApp();
  const days = rangeKeys(addDays(today, -13), 14);
  const done = completedByDay(data.items);
  const focus = new Map<string, number>();
  for (const f of data.focus) focus.set(f.date, (focus.get(f.date) ?? 0) + f.minutes);

  const openTasks = data.items.filter((i) => i.kind === "task" && i.repeat.freq === "none" && !i.done);
  const overdue = openTasks.filter((i) => i.date && i.date < today).length;
  const doneWeek = rangeKeys(addDays(today, -6), 7).reduce((s, d) => s + (done.get(d) ?? 0), 0);
  const focusWeek = rangeKeys(addDays(today, -6), 7).reduce((s, d) => s + (focus.get(d) ?? 0), 0);

  const byCategory = [
    ...data.categories.map((c) => ({ name: c.name, color: c.color, count: openTasks.filter((i) => i.categoryId === c.id).length })),
    { name: "미분류", color: "var(--muted)", count: openTasks.filter((i) => !i.categoryId).length },
  ].filter((c) => c.count > 0);
  const maxCat = Math.max(1, ...byCategory.map((c) => c.count));

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <h1 className="text-2xl font-bold">통계</h1>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Tile label="최근 7일 완료" value={doneWeek} unit="개" />
        <Tile label="최근 7일 집중" value={Math.round((focusWeek / 60) * 10) / 10} unit="시간" />
        <Tile label="남은 할일" value={openTasks.length} unit="개" />
        <Tile label="기한 지남" value={overdue} unit="개" warn={overdue > 0} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <BarChart title="완료한 할일 (최근 14일)" days={days} values={days.map((d) => done.get(d) ?? 0)} unit="개" today={today} />
        <BarChart title="집중 시간 (최근 14일)" days={days} values={days.map((d) => focus.get(d) ?? 0)} unit="분" today={today} />
      </div>
      <section className="rounded-2xl border border-line bg-surface p-4">
        <h2 className="mb-3 text-sm font-semibold">카테고리별 남은 할일</h2>
        {byCategory.length === 0 && <p className="text-sm text-muted">남은 할일이 없어요.</p>}
        <div className="space-y-2">
          {byCategory.map((c) => (
            <div key={c.name} className="flex items-center gap-3 text-sm">
              <span className="flex w-20 shrink-0 items-center gap-1.5 truncate">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: c.color }} />
                {c.name}
              </span>
              <div className="h-3 flex-1">
                <div className="h-full rounded-r-[4px]" style={{ width: `${(c.count / maxCat) * 100}%`, background: c.color }} />
              </div>
              <span className="w-8 text-right tabular-nums text-muted">{c.count}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Tile({ label, value, unit, warn }: { label: string; value: number; unit: string; warn?: boolean }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${warn ? "text-danger" : ""}`}>
        {value}
        <span className="ml-0.5 text-sm font-medium text-muted">{unit}</span>
      </div>
    </div>
  );
}

/** 단일 계열 막대 차트. 막대에 마우스를 올리면 값이 보인다. */
function BarChart({ title, days, values, unit, today }: { title: string; days: string[]; values: number[]; unit: string; today: string }) {
  const max = Math.max(1, ...values);
  const total = values.reduce((a, b) => a + b, 0);
  return (
    <section className="rounded-2xl border border-line bg-surface p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold">{title}</h2>
        <span className="text-xs text-muted tabular-nums">
          합계 {total}
          {unit}
        </span>
      </div>
      <div className="relative flex h-36 items-end gap-[2px] border-b border-line">
        {values.map((v, i) => (
          <div key={days[i]} className="group relative flex h-full flex-1 items-end justify-center">
            <div
              className="w-full max-w-5 rounded-t-[4px] transition-opacity group-hover:opacity-80"
              style={{ height: `${(v / max) * 100}%`, minHeight: v > 0 ? 3 : 0, background: "var(--accent)" }}
            />
            <div className="pointer-events-none absolute bottom-full mb-1 hidden rounded-md border border-line bg-surface px-2 py-1 text-[11px] whitespace-nowrap shadow group-hover:block">
              {fromKey(days[i]).getMonth() + 1}/{fromKey(days[i]).getDate()} · {v}
              {unit}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-[2px] text-center text-[10px] text-muted">
        {days.map((d) => (
          <div key={d} className={`flex-1 ${d === today ? "font-semibold text-accent" : ""}`}>
            {WEEKDAYS[fromKey(d).getDay()]}
          </div>
        ))}
      </div>
    </section>
  );
}
