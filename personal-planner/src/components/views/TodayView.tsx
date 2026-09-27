"use client";

import { useState } from "react";
import { addDays, formatDate, relativeLabel } from "@/lib/date";
import { holidayName } from "@/lib/holidays";
import { expandRange } from "@/lib/recurrence";
import { useStore } from "@/lib/store";
import { useApp } from "../AppContext";
import { ItemRow } from "../ItemRow";
import { QuickAdd } from "../QuickAdd";
import { Button, Checkbox, Icon } from "../ui";

function greeting(hour: number) {
  if (hour < 6) return "늦은 밤이에요";
  if (hour < 12) return "좋은 아침이에요";
  if (hour < 18) return "좋은 오후예요";
  return "좋은 저녁이에요";
}

export function TodayView() {
  const { data, dispatch } = useStore();
  const { today, now, goToDate } = useApp();
  const [showDone, setShowDone] = useState(false);

  const week = expandRange(data.items, today, addDays(today, 7));
  const todays = week.get(today) ?? [];
  const pending = todays.filter((o) => !o.done);
  const done = todays.filter((o) => o.done);
  const overdue = data.items
    .filter((i) => i.kind === "task" && i.repeat.freq === "none" && !i.done && i.date && i.date < today)
    .sort((a, b) => (a.date! < b.date! ? -1 : 1));
  const inboxCount = data.items.filter((i) => !i.date && !i.done).length;
  const upcoming = Array.from({ length: 7 }, (_, i) => addDays(today, i + 1))
    .map((d) => ({ date: d, list: (week.get(d) ?? []).filter((o) => !o.done) }))
    .filter((d) => d.list.length > 0);

  const total = todays.filter((o) => o.item.kind === "task").length;
  const completed = done.filter((o) => o.item.kind === "task").length;
  const focusToday = data.focus.filter((f) => f.date === today).reduce((s, f) => s + f.minutes, 0);
  const holiday = data.settings.showHolidays ? holidayName(today) : undefined;

  return (
    <div className="mx-auto grid max-w-6xl gap-6 p-4 sm:p-6 lg:grid-cols-[1fr_320px]">
      <div className="min-w-0 space-y-5">
        <header>
          <p className="text-sm text-muted">{greeting(now.getHours())} 👋</p>
          <h1 className="mt-1 text-2xl font-bold">
            {formatDate(today, true)}
            {holiday && <span className="ml-2 align-middle text-sm font-medium text-holiday">{holiday}</span>}
          </h1>
        </header>

        <QuickAdd defaults={{ date: today }} placeholder="오늘 할 일 추가 (예: 3시 치과 30분, 장보기 !2)" />

        {overdue.length > 0 && (
          <section className="rounded-2xl border border-line bg-surface p-2">
            <div className="flex items-center justify-between px-3 py-2">
              <h2 className="text-sm font-semibold text-danger">지난 할일 {overdue.length}</h2>
              <Button
                variant="ghost"
                className="text-xs"
                onClick={() => overdue.forEach((i) => dispatch({ type: "updateItem", id: i.id, patch: { date: today } }))}
              >
                모두 오늘로 옮기기
              </Button>
            </div>
            {overdue.map((i) => (
              <ItemRow key={i.id} item={i} />
            ))}
          </section>
        )}

        <section className="rounded-2xl border border-line bg-surface p-2">
          <div className="flex items-center justify-between px-3 py-2">
            <h2 className="text-sm font-semibold">오늘</h2>
            <span className="text-xs text-muted">{pending.length}개 남음</span>
          </div>
          {pending.length === 0 && (
            <p className="px-3 pb-4 pt-1 text-sm text-muted">
              {todays.length === 0 ? "오늘 예정된 항목이 없어요. 위에서 추가해보세요." : "오늘 할 일을 모두 끝냈어요! 🎉"}
            </p>
          )}
          {pending.map((o) => (
            <ItemRow key={o.item.id + o.date} item={o.item} date={o.date} done={o.done} showDate={false} />
          ))}
          {done.length > 0 && (
            <>
              <button onClick={() => setShowDone((v) => !v)} className="mx-3 my-2 text-xs text-muted hover:text-ink">
                {showDone ? "▾" : "▸"} 완료됨 {done.length}
              </button>
              {showDone &&
                done.map((o) => (
                  <ItemRow key={o.item.id + o.date} item={o.item} date={o.date} done={o.done} showDate={false} />
                ))}
            </>
          )}
        </section>
      </div>

      <aside className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          <Stat label="오늘 완료" value={`${completed}/${total}`} />
          <Stat label="집중" value={`${focusToday}분`} />
          <Stat label="수집함" value={String(inboxCount)} />
        </div>
        {total > 0 && (
          <div className="rounded-2xl border border-line bg-surface p-4">
            <div className="mb-2 flex justify-between text-xs text-muted">
              <span>오늘 진행률</span>
              <span>{Math.round((completed / total) * 100)}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${(completed / total) * 100}%` }} />
            </div>
          </div>
        )}

        {data.habits.length > 0 && (
          <div className="rounded-2xl border border-line bg-surface p-4">
            <h3 className="mb-3 text-sm font-semibold">오늘의 습관</h3>
            <div className="space-y-2">
              {data.habits.map((h) => (
                <label key={h.id} className="flex cursor-pointer items-center gap-3 text-sm">
                  <Checkbox
                    checked={h.log.includes(today)}
                    color={h.color}
                    onChange={() => dispatch({ type: "toggleHabit", id: h.id, date: today })}
                  />
                  <span className={h.log.includes(today) ? "text-muted line-through" : ""}>{h.name}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-line bg-surface p-4">
          <h3 className="mb-2 text-sm font-semibold">다가오는 일정</h3>
          {upcoming.length === 0 && <p className="text-sm text-muted">앞으로 7일간 예정된 항목이 없어요.</p>}
          <div className="space-y-3">
            {upcoming.map(({ date, list }) => (
              <div key={date}>
                <button onClick={() => goToDate(date, "day")} className="mb-1 text-xs font-semibold text-muted hover:text-accent">
                  {relativeLabel(date, today)}
                </button>
                {list.slice(0, 4).map((o) => (
                  <ItemRow key={o.item.id + o.date} item={o.item} date={o.date} done={o.done} compact />
                ))}
                {list.length > 4 && <p className="px-3 text-xs text-muted">외 {list.length - 4}개</p>}
              </div>
            ))}
          </div>
          <button onClick={() => goToDate(today, "week")} className="mt-3 flex items-center gap-1 text-xs text-accent">
            <Icon name="calendar" size={14} /> 캘린더에서 보기
          </button>
        </div>
      </aside>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-3 text-center">
      <div className="text-lg font-bold">{value}</div>
      <div className="text-[11px] text-muted">{label}</div>
    </div>
  );
}
