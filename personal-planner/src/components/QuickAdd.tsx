"use client";

import { useState, type Ref } from "react";
import { formatTime, relativeLabel } from "@/lib/date";
import { parseQuickAdd } from "@/lib/quickAdd";
import { repeatText } from "@/lib/recurrence";
import { newItem, useStore } from "@/lib/store";
import type { Item } from "@/lib/types";
import { useApp } from "./AppContext";
import { Chip, Icon, PRIORITY_META } from "./ui";

/**
 * 한 줄 입력으로 할일/일정을 추가한다.
 * defaults는 입력에서 찾지 못한 값을 채울 기본값 (예: 캘린더에서 선택한 날짜).
 */
export function QuickAdd({
  defaults,
  placeholder,
  ref,
}: {
  defaults?: Partial<Item>;
  placeholder?: string;
  ref?: Ref<HTMLInputElement>;
}) {
  const { data, dispatch, categoryById } = useStore();
  const { today } = useApp();
  const [text, setText] = useState("");
  const parsed = text.trim() ? parseQuickAdd(text, today, data.categories) : null;

  const submit = () => {
    if (!parsed || !parsed.title) return;
    const { title, ...rest } = parsed;
    dispatch({
      type: "addItem",
      item: newItem({
        ...defaults,
        title,
        kind: (rest.start ?? defaults?.start) ? "event" : "task",
        date: rest.date ?? defaults?.date,
        start: rest.start ?? defaults?.start,
        end: rest.end ?? defaults?.end,
        priority: rest.priority !== 4 ? rest.priority : defaults?.priority,
        tags: rest.tags,
        categoryId: rest.categoryId ?? defaults?.categoryId,
        repeat: rest.repeat,
      }),
    });
    setText("");
  };

  const category = parsed?.categoryId ? categoryById.get(parsed.categoryId) : undefined;

  return (
    <div data-quickadd className="rounded-xl border border-line bg-surface shadow-sm focus-within:border-accent">
      <div className="flex items-center gap-2 px-3">
        <Icon name="plus" className="text-accent" />
        <input
          ref={ref}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
            if (e.key === "Escape") {
              setText("");
              e.currentTarget.blur();
            }
          }}
          placeholder={placeholder ?? "빠르게 추가: 내일 오후 3시 회의 #업무 !1"}
          className="h-11 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
        />
        {parsed?.title && (
          <button onClick={submit} className="rounded-lg bg-accent px-3 py-1 text-xs font-semibold text-white">
            추가
          </button>
        )}
      </div>
      {parsed && (parsed.date || parsed.start || parsed.tags.length > 0 || parsed.priority !== 4 || category || parsed.repeat.freq !== "none") && (
        <div className="flex flex-wrap items-center gap-1.5 border-t border-line px-3 py-2">
          <Chip color="var(--accent)">{parsed.kind === "event" ? "일정" : "할일"}</Chip>
          {parsed.date && <Chip color="#0ea5e9">{relativeLabel(parsed.date, today)}</Chip>}
          {parsed.start && (
            <Chip color="#0ea5e9">
              {formatTime(parsed.start)}
              {parsed.end && ` ~ ${formatTime(parsed.end)}`}
            </Chip>
          )}
          {parsed.repeat.freq !== "none" && <Chip color="#8b5cf6">{repeatText(parsed.repeat)}</Chip>}
          {parsed.priority !== 4 && (
            <Chip color={PRIORITY_META[parsed.priority].color}>{PRIORITY_META[parsed.priority].label}</Chip>
          )}
          {category && <Chip color={category.color}>{category.name}</Chip>}
          {parsed.tags.map((t) => (
            <Chip key={t}>#{t}</Chip>
          ))}
        </div>
      )}
    </div>
  );
}
