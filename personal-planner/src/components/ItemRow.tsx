"use client";

import { diffDays, formatTime, relativeLabel } from "@/lib/date";
import { repeatText } from "@/lib/recurrence";
import { useStore } from "@/lib/store";
import type { Item } from "@/lib/types";
import { DRAG_TYPE, useApp, type DragPayload } from "./AppContext";
import { Checkbox, Chip, Icon, PRIORITY_META } from "./ui";

export function ItemRow({
  item,
  date,
  done,
  showDate = true,
  compact = false,
}: {
  item: Item;
  /** 표시할 발생 날짜 (반복 항목이면 해당 회차) */
  date?: string;
  done?: boolean;
  showDate?: boolean;
  compact?: boolean;
}) {
  const { dispatch, categoryById } = useStore();
  const { today, openEdit, startFocus } = useApp();
  const occDate = date ?? item.date;
  const isDone = done ?? (item.repeat.freq === "none" ? item.done : !!occDate && item.doneDates.includes(occDate));
  const category = item.categoryId ? categoryById.get(item.categoryId) : undefined;
  const overdue = !isDone && occDate && occDate < today;
  const subDone = item.subtasks.filter((s) => s.done).length;

  return (
    <div
      draggable
      onDragStart={(e) => {
        const payload: DragPayload = { id: item.id, from: occDate };
        e.dataTransfer.setData(DRAG_TYPE, JSON.stringify(payload));
        e.dataTransfer.effectAllowed = "move";
      }}
      onClick={() => openEdit(item, occDate)}
      className={`group flex cursor-pointer items-start gap-3 rounded-xl px-3 ${compact ? "py-1.5" : "py-2.5"} hover:bg-surface-2`}
    >
      <div className="pt-0.5">
        {item.kind === "task" ? (
          <Checkbox
            checked={isDone}
            color={PRIORITY_META[item.priority].color}
            onChange={() => dispatch({ type: "toggleDone", id: item.id, date: occDate })}
          />
        ) : (
          <span
            className="mt-0.5 block h-4 w-1.5 rounded-full"
            style={{ background: category?.color ?? "var(--accent)" }}
            title="일정"
          />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className={`truncate text-sm ${isDone ? "text-muted line-through" : ""}`}>{item.title || "(제목 없음)"}</div>
        {!compact && (
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted">
            {showDate && occDate && (
              <span className={overdue ? "font-medium text-danger" : ""}>
                {relativeLabel(occDate, today)}
                {overdue && ` · ${diffDays(occDate, today)}일 지남`}
              </span>
            )}
            {item.start && (
              <span className="inline-flex items-center gap-0.5">
                <Icon name="clock" size={12} />
                {formatTime(item.start)}
                {item.end && ` ~ ${formatTime(item.end)}`}
              </span>
            )}
            {item.repeat.freq !== "none" && (
              <span className="inline-flex items-center gap-0.5">
                <Icon name="repeat" size={12} />
                {repeatText(item.repeat)}
              </span>
            )}
            {item.subtasks.length > 0 && (
              <span>
                ☑ {subDone}/{item.subtasks.length}
              </span>
            )}
            {item.notes && <Icon name="note" size={12} />}
            {item.reminder !== undefined && <Icon name="bell" size={12} />}
            {category && <Chip color={category.color}>{category.name}</Chip>}
            {item.tags.map((t) => (
              <Chip key={t}>#{t}</Chip>
            ))}
          </div>
        )}
      </div>
      {item.kind === "task" && !isDone && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            startFocus(item.id);
          }}
          title="이 할일로 집중 타이머 시작"
          className="rounded-md p-1 text-muted opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-accent max-sm:opacity-60"
        >
          <Icon name="timer" size={16} />
        </button>
      )}
    </div>
  );
}
