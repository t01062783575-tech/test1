"use client";

import { useState } from "react";
import { addDays } from "@/lib/date";
import { nextOccurrence } from "@/lib/recurrence";
import { useStore } from "@/lib/store";
import type { Item, Priority } from "@/lib/types";
import { DRAG_TYPE, useApp, type DragPayload } from "../AppContext";
import { ItemRow } from "../ItemRow";

// 아이젠하워 매트릭스: 중요도 = 우선순위(1·2), 긴급도 = 2일 이내 마감
const QUADRANTS = [
  { key: "do", title: "지금 하기", desc: "중요 · 긴급", color: "#ef4444", important: true, urgent: true },
  { key: "plan", title: "계획하기", desc: "중요 · 여유", color: "#6366f1", important: true, urgent: false },
  { key: "delegate", title: "빠르게 처리", desc: "덜 중요 · 긴급", color: "#f59e0b", important: false, urgent: true },
  { key: "later", title: "나중에", desc: "덜 중요 · 여유", color: "#64748b", important: false, urgent: false },
] as const;

export function MatrixView() {
  const { data, dispatch } = useStore();
  const { today } = useApp();
  const [over, setOver] = useState<string | null>(null);
  const soon = addDays(today, 2);

  const tasks = data.items
    .filter((i) => i.kind === "task")
    .map((item) => ({ item, date: item.repeat.freq === "none" ? item.date : nextOccurrence(item, today) }))
    .filter(({ item, date }) => (item.repeat.freq === "none" ? !item.done : !!date));

  const isImportant = (i: Item) => i.priority <= 2;
  const isUrgent = (d?: string) => !!d && d <= soon;

  /** 사분면으로 옮기면 우선순위/날짜를 그에 맞게 바꾼다. */
  const dropTo = (q: (typeof QUADRANTS)[number], payload: DragPayload) => {
    const item = data.items.find((i) => i.id === payload.id);
    if (!item) return;
    const patch: Partial<Item> = {};
    if (q.important !== isImportant(item)) patch.priority = (q.important ? 2 : 3) as Priority;
    const date = item.repeat.freq === "none" ? item.date : nextOccurrence(item, today);
    if (q.urgent && !isUrgent(date) && item.repeat.freq === "none") patch.date = today;
    if (!q.urgent && isUrgent(date) && item.repeat.freq === "none") patch.date = addDays(today, 7);
    dispatch({ type: "updateItem", id: item.id, patch });
  };

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col p-4 sm:p-6">
      <h1 className="text-2xl font-bold">우선순위 매트릭스</h1>
      <p className="mt-1 mb-4 text-sm text-muted">
        중요도(우선순위 1·2)와 긴급도(2일 이내 마감)로 할일을 나눠요. 칸 사이로 끌어서 옮기면 우선순위와 날짜가 바뀌어요.
      </p>
      <div className="grid flex-1 gap-3 md:grid-cols-2 md:grid-rows-2">
        {QUADRANTS.map((q) => {
          const list = tasks.filter(({ item, date }) => isImportant(item) === q.important && isUrgent(date) === q.urgent);
          return (
            <section
              key={q.key}
              onDragOver={(e) => {
                if (e.dataTransfer.types.includes(DRAG_TYPE)) {
                  e.preventDefault();
                  setOver(q.key);
                }
              }}
              onDragLeave={() => setOver(null)}
              onDrop={(e) => {
                e.preventDefault();
                setOver(null);
                try {
                  dropTo(q, JSON.parse(e.dataTransfer.getData(DRAG_TYPE)));
                } catch {
                  // 잘못된 드롭 무시
                }
              }}
              className={`flex min-h-48 flex-col rounded-2xl border bg-surface p-2 transition ${over === q.key ? "border-accent" : "border-line"}`}
              style={{ borderTopWidth: 4, borderTopColor: q.color }}
            >
              <div className="flex items-baseline gap-2 px-3 py-2">
                <h2 className="font-semibold" style={{ color: q.color }}>
                  {q.title}
                </h2>
                <span className="text-xs text-muted">{q.desc}</span>
                <span className="ml-auto text-xs text-muted">{list.length}</span>
              </div>
              <div className="scroll-thin flex-1 overflow-y-auto">
                {list.map(({ item, date }) => (
                  <ItemRow key={item.id} item={item} date={date} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
