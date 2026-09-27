"use client";

import { useState } from "react";
import { relativeLabel } from "@/lib/date";
import { nextOccurrence } from "@/lib/recurrence";
import { useStore } from "@/lib/store";
import type { View } from "@/lib/types";
import { useApp } from "./AppContext";
import { Icon, Modal } from "./ui";

interface Result {
  key: string;
  label: string;
  hint?: string;
  run: () => void;
}

const VIEW_COMMANDS: { view: View; label: string }[] = [
  { view: "today", label: "오늘로 이동" },
  { view: "calendar", label: "캘린더로 이동" },
  { view: "tasks", label: "할일 목록으로 이동" },
  { view: "matrix", label: "우선순위 매트릭스로 이동" },
  { view: "habits", label: "습관 트래커로 이동" },
  { view: "stats", label: "통계로 이동" },
];

/** Ctrl/⌘ + K 검색·명령 팔레트 */
export function SearchPalette({ open, onClose, onView }: { open: boolean; onClose: () => void; onView: (v: View) => void }) {
  return (
    <Modal open={open} onClose={onClose}>
      {open && <PaletteBody onClose={onClose} onView={onView} />}
    </Modal>
  );
}

function PaletteBody({ onClose, onView }: { onClose: () => void; onView: (v: View) => void }) {
  const { data } = useStore();
  const { today, openEdit, openNew, startFocus } = useApp();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const query = q.trim().toLowerCase();

  const commands: Result[] = [
    { key: "new", label: "새 할일/일정 만들기", hint: "N", run: () => openNew() },
    { key: "focus", label: "집중 타이머 시작", hint: "F", run: () => startFocus() },
    ...VIEW_COMMANDS.map((c) => ({ key: c.view, label: c.label, run: () => onView(c.view) })),
  ].filter((c) => !query || c.label.toLowerCase().includes(query));

  const items: Result[] = query
    ? data.items
        .filter(
          (i) =>
            i.title.toLowerCase().includes(query) ||
            i.notes.toLowerCase().includes(query) ||
            i.tags.some((t) => t.toLowerCase().includes(query)),
        )
        .slice(0, 30)
        .map((i) => {
          const date = i.repeat.freq === "none" ? i.date : (nextOccurrence(i, today) ?? i.date);
          return {
            key: i.id,
            label: `${i.kind === "task" ? (i.done ? "☑" : "☐") : "📅"} ${i.title}`,
            hint: date ? relativeLabel(date, today) : "날짜 없음",
            run: () => openEdit(i, date),
          };
        })
    : [];

  const results = [...items, ...commands];
  const active = Math.min(sel, results.length - 1);

  const choose = (r: Result | undefined) => {
    if (!r) return;
    onClose();
    r.run();
  };

  return (
    <div>
      <div className="flex items-center gap-2 border-b border-line px-4">
        <Icon name="search" className="text-muted" />
        <input
          autoFocus
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setSel(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setSel((s) => Math.min(results.length - 1, s + 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setSel((s) => Math.max(0, s - 1));
            } else if (e.key === "Enter" && !e.nativeEvent.isComposing) {
              e.preventDefault();
              choose(results[active]);
            }
          }}
          placeholder="할일·일정 검색 또는 명령 입력"
          className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
        />
        <kbd className="rounded border border-line px-1.5 text-[10px] text-muted">ESC</kbd>
      </div>
      <div className="scroll-thin max-h-[60vh] overflow-y-auto p-2">
        {results.length === 0 && <p className="px-3 py-6 text-center text-sm text-muted">결과가 없어요.</p>}
        {query && items.length > 0 && <div className="px-3 pt-1 pb-1 text-[11px] font-semibold text-muted">항목</div>}
        {results.map((r, idx) => (
          <div key={r.key}>
            {idx === items.length && <div className="px-3 pt-2 pb-1 text-[11px] font-semibold text-muted">명령</div>}
            <button
              onMouseEnter={() => setSel(idx)}
              onClick={() => choose(r)}
              className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm ${
                idx === active ? "bg-accent-soft" : ""
              }`}
            >
              <span className="truncate">{r.label}</span>
              {r.hint && <span className="shrink-0 text-xs text-muted">{r.hint}</span>}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
