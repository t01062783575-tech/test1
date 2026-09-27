"use client";

import { useState } from "react";
import { addDays } from "@/lib/date";
import { nextOccurrence } from "@/lib/recurrence";
import { useStore } from "@/lib/store";
import type { Item } from "@/lib/types";
import { useApp } from "../AppContext";
import { ItemRow } from "../ItemRow";
import { QuickAdd } from "../QuickAdd";
import { Icon } from "../ui";

export type TaskFilter =
  | { type: "inbox" }
  | { type: "today" }
  | { type: "week" }
  | { type: "all" }
  | { type: "done" }
  | { type: "category"; id: string }
  | { type: "tag"; tag: string };

type Sort = "date" | "priority" | "created";

export function TasksView({ filter, onFilter }: { filter: TaskFilter; onFilter: (f: TaskFilter) => void }) {
  const { data, categoryById } = useStore();
  const { today } = useApp();
  const [sort, setSort] = useState<Sort>("date");
  const [includeEvents, setIncludeEvents] = useState(false);

  const allTags = Array.from(new Set(data.items.flatMap((i) => i.tags))).sort((a, b) => a.localeCompare(b, "ko"));

  // 각 항목을 "다음에 해야 할 날짜"와 함께 본다
  const rows = data.items
    .filter((i) => includeEvents || i.kind === "task" || filter.type === "done")
    .map((item) => {
      const date = item.repeat.freq === "none" ? item.date : (nextOccurrence(item, today) ?? item.date);
      return { item, date, done: item.repeat.freq === "none" ? item.done : !nextOccurrence(item, today) };
    });

  const inRange = (d: string | undefined, to: string) => !!d && d <= to;
  const filtered = rows.filter(({ item, date, done }) => {
    switch (filter.type) {
      case "inbox":
        return !item.date && !done;
      case "today":
        return !done && inRange(date, today);
      case "week":
        return !done && inRange(date, addDays(today, 6));
      case "all":
        return !done;
      case "done":
        return done;
      case "category":
        return !done && item.categoryId === filter.id;
      case "tag":
        return !done && item.tags.includes(filter.tag);
    }
  });

  const cmp = (a: { item: Item; date?: string }, b: { item: Item; date?: string }) => {
    if (sort === "priority" && a.item.priority !== b.item.priority) return a.item.priority - b.item.priority;
    if (sort === "created") return a.item.createdAt < b.item.createdAt ? 1 : -1;
    if (filter.type === "done") return (b.item.completedAt ?? "") < (a.item.completedAt ?? "") ? -1 : 1;
    const ad = a.date ?? "9999";
    const bd = b.date ?? "9999";
    if (ad !== bd) return ad < bd ? -1 : 1;
    if ((a.item.start ?? "") !== (b.item.start ?? "")) return (a.item.start ?? "") < (b.item.start ?? "") ? -1 : 1;
    return a.item.priority - b.item.priority;
  };
  filtered.sort(cmp);

  const title = {
    inbox: "수집함",
    today: "오늘까지",
    week: "다음 7일",
    all: "모든 할일",
    done: "완료됨",
    category: filter.type === "category" ? (categoryById.get(filter.id)?.name ?? "카테고리") : "",
    tag: filter.type === "tag" ? `#${filter.tag}` : "",
  }[filter.type];

  const defaults: Partial<Item> =
    filter.type === "category"
      ? { categoryId: filter.id }
      : filter.type === "tag"
        ? { tags: [filter.tag] }
        : filter.type === "today"
          ? { date: today }
          : {};

  const tabs: { f: TaskFilter; label: string; icon: Parameters<typeof Icon>[0]["name"] }[] = [
    { f: { type: "inbox" }, label: "수집함", icon: "inbox" },
    { f: { type: "today" }, label: "오늘", icon: "sun" },
    { f: { type: "week" }, label: "7일", icon: "calendar" },
    { f: { type: "all" }, label: "전체", icon: "list" },
    { f: { type: "done" }, label: "완료", icon: "check" },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <div className="scroll-thin -mx-1 flex gap-1 overflow-x-auto px-1 pb-1">
        {tabs.map((t) => (
          <button
            key={t.f.type}
            onClick={() => onFilter(t.f)}
            className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm ${
              filter.type === t.f.type ? "bg-accent text-white" : "bg-surface-2 text-muted hover:text-ink"
            }`}
          >
            <Icon name={t.icon} size={15} /> {t.label}
          </button>
        ))}
        {data.categories.map((c) => (
          <button
            key={c.id}
            onClick={() => onFilter({ type: "category", id: c.id })}
            className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm ${
              filter.type === "category" && filter.id === c.id ? "text-white" : "bg-surface-2 text-muted hover:text-ink"
            }`}
            style={filter.type === "category" && filter.id === c.id ? { background: c.color } : undefined}
          >
            <span className="h-2 w-2 rounded-full" style={{ background: c.color }} /> {c.name}
          </button>
        ))}
        {allTags.map((t) => (
          <button
            key={t}
            onClick={() => onFilter({ type: "tag", tag: t })}
            className={`shrink-0 rounded-full px-3 py-1.5 text-sm ${
              filter.type === "tag" && filter.tag === t ? "bg-accent text-white" : "bg-surface-2 text-muted hover:text-ink"
            }`}
          >
            #{t}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-end justify-between gap-2">
        <h1 className="text-2xl font-bold">
          {title} <span className="text-base font-normal text-muted">{filtered.length}</span>
        </h1>
        <div className="flex items-center gap-3 text-xs text-muted">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={includeEvents} onChange={(e) => setIncludeEvents(e.target.checked)} className="accent-[var(--accent)]" />
            일정 포함
          </label>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} className="rounded-md border border-line bg-surface px-2 py-1">
            <option value="date">날짜순</option>
            <option value="priority">우선순위순</option>
            <option value="created">최근 추가순</option>
          </select>
        </div>
      </div>

      {filter.type !== "done" && <QuickAdd defaults={defaults} />}

      <div className="rounded-2xl border border-line bg-surface p-2">
        {filtered.length === 0 && (
          <p className="px-3 py-8 text-center text-sm text-muted">
            {filter.type === "inbox" ? "수집함이 비었어요. 생각나는 일을 바로 적어두세요." : "표시할 항목이 없어요."}
          </p>
        )}
        {filtered.map(({ item, date, done }) => (
          <ItemRow key={item.id} item={item} date={date} done={done} />
        ))}
      </div>
    </div>
  );
}
