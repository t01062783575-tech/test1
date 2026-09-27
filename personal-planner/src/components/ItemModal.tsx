"use client";

import { useState } from "react";
import { formatDate, minToTime, timeToMin } from "@/lib/date";
import { REPEAT_LABEL } from "@/lib/recurrence";
import { uid, useStore } from "@/lib/store";
import type { Item, Priority, RepeatFreq } from "@/lib/types";
import { Button, Checkbox, Icon, Modal, PRIORITY_META } from "./ui";

const REMINDERS: { value: string; label: string }[] = [
  { value: "", label: "알림 없음" },
  { value: "0", label: "정시에" },
  { value: "5", label: "5분 전" },
  { value: "10", label: "10분 전" },
  { value: "30", label: "30분 전" },
  { value: "60", label: "1시간 전" },
  { value: "1440", label: "하루 전" },
];

const input =
  "w-full rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm outline-none focus:border-accent";
const label = "mb-1 block text-xs font-medium text-muted";

export interface Editing {
  item: Item;
  isNew: boolean;
  occurrenceDate?: string;
}

export function ItemModal({ editing, onClose }: { editing: Editing | null; onClose: () => void }) {
  return (
    <Modal open={!!editing} onClose={onClose} wide>
      {editing && <ItemForm key={editing.item.id} editing={editing} onClose={onClose} />}
    </Modal>
  );
}

function ItemForm({ editing, onClose }: { editing: Editing; onClose: () => void }) {
  const { data, dispatch } = useStore();
  const [draft, setDraft] = useState<Item>(editing.item);
  const [tagText, setTagText] = useState(editing.item.tags.join(", "));
  const [subText, setSubText] = useState("");
  const set = (patch: Partial<Item>) => setDraft((d) => ({ ...d, ...patch }));
  const isRepeat = draft.repeat.freq !== "none";
  const allDay = !draft.start;

  const save = () => {
    const item: Item = {
      ...draft,
      title: draft.title.trim() || "(제목 없음)",
      tags: tagText
        .split(/[,\s]+/)
        .map((t) => t.replace(/^#/, "").trim())
        .filter(Boolean),
    };
    if (editing.isNew) dispatch({ type: "addItem", item });
    else dispatch({ type: "updateItem", id: item.id, patch: item });
    onClose();
  };

  const remove = (onlyThis: boolean) => {
    if (onlyThis && editing.occurrenceDate) {
      dispatch({ type: "skipOccurrence", id: draft.id, date: editing.occurrenceDate });
    } else {
      dispatch({ type: "deleteItem", id: draft.id });
    }
    onClose();
  };

  const addSubtask = () => {
    const title = subText.trim();
    if (!title) return;
    set({ subtasks: [...draft.subtasks, { id: uid(), title, done: false }] });
    setSubText("");
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save();
      }}
    >
      <div className="flex items-center gap-2 border-b border-line px-5 py-3">
        <div className="flex rounded-lg bg-surface-2 p-0.5 text-sm">
          {(["task", "event"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() =>
                set(
                  k === "event" && !draft.start
                    ? { kind: k, date: draft.date ?? editing.occurrenceDate, start: "09:00", end: "10:00" }
                    : { kind: k },
                )
              }
              className={`rounded-md px-3 py-1 ${draft.kind === k ? "bg-surface font-semibold shadow-sm" : "text-muted"}`}
            >
              {k === "task" ? "할일" : "일정"}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <button type="button" onClick={onClose} className="rounded-md p-1 text-muted hover:bg-surface-2" aria-label="닫기">
          <Icon name="x" />
        </button>
      </div>

      <div className="space-y-4 px-5 py-4">
        <input
          autoFocus
          value={draft.title}
          onChange={(e) => set({ title: e.target.value })}
          placeholder={draft.kind === "task" ? "무엇을 해야 하나요?" : "일정 제목"}
          className="w-full bg-transparent text-lg font-semibold outline-none placeholder:text-muted"
        />

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="col-span-2">
            <label className={label}>날짜</label>
            <div className="flex gap-2">
              <input
                type="date"
                value={draft.date ?? ""}
                onChange={(e) => set({ date: e.target.value || undefined })}
                className={input}
              />
              {draft.date && (
                <button type="button" onClick={() => set({ date: undefined, start: undefined, end: undefined, repeat: { freq: "none", interval: 1 } })} className="text-xs text-muted hover:text-ink" title="날짜 지우기">
                  <Icon name="x" size={16} />
                </button>
              )}
            </div>
          </div>
          <div className="col-span-2 flex items-end gap-2">
            <label className="flex h-9 shrink-0 items-center gap-2 text-sm whitespace-nowrap">
              <Checkbox
                round={false}
                checked={allDay}
                onChange={() =>
                  set(allDay ? { start: "09:00", end: "10:00", date: draft.date ?? editing.occurrenceDate } : { start: undefined, end: undefined })
                }
                label="종일"
              />
              종일
            </label>
            {!allDay && (
              <>
                <input
                  type="time"
                  value={draft.start ?? ""}
                  onChange={(e) => {
                    const start = e.target.value;
                    if (!start) return;
                    // 시작을 옮기면 기존 길이를 유지
                    const len = draft.start && draft.end ? timeToMin(draft.end) - timeToMin(draft.start) : 60;
                    set({ start, end: minToTime(timeToMin(start) + Math.max(15, len)) });
                  }}
                  className={input}
                />
                <input
                  type="time"
                  value={draft.end ?? ""}
                  onChange={(e) => set({ end: e.target.value || undefined })}
                  className={input}
                />
              </>
            )}
          </div>
        </div>

        {draft.date && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="col-span-2">
              <label className={label}>반복</label>
              <select
                value={draft.repeat.freq}
                onChange={(e) => set({ repeat: { ...draft.repeat, freq: e.target.value as RepeatFreq } })}
                className={input}
              >
                {Object.entries(REPEAT_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            {isRepeat && draft.repeat.freq !== "weekdays" && (
              <div>
                <label className={label}>간격</label>
                <input
                  type="number"
                  min={1}
                  max={99}
                  value={draft.repeat.interval}
                  onChange={(e) => set({ repeat: { ...draft.repeat, interval: Math.max(1, Number(e.target.value) || 1) } })}
                  className={input}
                />
              </div>
            )}
            {isRepeat && (
              <div>
                <label className={label}>종료일</label>
                <input
                  type="date"
                  value={draft.repeat.until ?? ""}
                  onChange={(e) => set({ repeat: { ...draft.repeat, until: e.target.value || undefined } })}
                  className={input}
                />
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className={label}>우선순위</label>
            <div className="flex gap-1">
              {([1, 2, 3, 4] as Priority[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => set({ priority: p })}
                  title={PRIORITY_META[p].label}
                  className={`flex h-9 flex-1 items-center justify-center rounded-lg border ${
                    draft.priority === p ? "border-accent bg-accent-soft" : "border-line"
                  }`}
                >
                  <span style={{ color: PRIORITY_META[p].color }}>
                    <Icon name="flag" size={16} />
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className={label}>카테고리</label>
            <select
              value={draft.categoryId ?? ""}
              onChange={(e) => set({ categoryId: e.target.value || undefined })}
              className={input}
            >
              <option value="">없음</option>
              {data.categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={label}>알림</label>
            <select
              value={draft.reminder === undefined ? "" : String(draft.reminder)}
              onChange={(e) => set({ reminder: e.target.value === "" ? undefined : Number(e.target.value) })}
              className={input}
              disabled={!draft.date}
            >
              {REMINDERS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className={label}>태그 (쉼표로 구분)</label>
          <input value={tagText} onChange={(e) => setTagText(e.target.value)} placeholder="예: 업무, 긴급" className={input} />
        </div>

        <div>
          <label className={label}>하위 할일</label>
          <div className="space-y-1">
            {draft.subtasks.map((s) => (
              <div key={s.id} className="group flex items-center gap-2 rounded-lg px-1 py-1 hover:bg-surface-2">
                <Checkbox
                  size={16}
                  checked={s.done}
                  onChange={() => set({ subtasks: draft.subtasks.map((x) => (x.id === s.id ? { ...x, done: !x.done } : x)) })}
                />
                <input
                  value={s.title}
                  onChange={(e) =>
                    set({ subtasks: draft.subtasks.map((x) => (x.id === s.id ? { ...x, title: e.target.value } : x)) })
                  }
                  className={`flex-1 bg-transparent text-sm outline-none ${s.done ? "text-muted line-through" : ""}`}
                />
                <button
                  type="button"
                  onClick={() => set({ subtasks: draft.subtasks.filter((x) => x.id !== s.id) })}
                  className="text-muted opacity-0 group-hover:opacity-100 hover:text-danger"
                  aria-label="하위 할일 삭제"
                >
                  <Icon name="x" size={14} />
                </button>
              </div>
            ))}
            <div className="flex items-center gap-2 px-1">
              <Icon name="plus" size={16} className="text-muted" />
              <input
                value={subText}
                onChange={(e) => setSubText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    addSubtask();
                  }
                }}
                placeholder="하위 할일 추가 후 Enter"
                className="flex-1 bg-transparent py-1 text-sm outline-none placeholder:text-muted"
              />
            </div>
          </div>
        </div>

        <div>
          <label className={label}>메모</label>
          <textarea
            value={draft.notes}
            onChange={(e) => set({ notes: e.target.value })}
            rows={3}
            placeholder="자세한 내용, 링크 등"
            className={`${input} resize-y`}
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3">
        {!editing.isNew &&
          (isRepeat && editing.occurrenceDate ? (
            <>
              <Button variant="danger" onClick={() => remove(true)} title={formatDate(editing.occurrenceDate)}>
                이 회차만 삭제
              </Button>
              <Button variant="danger" onClick={() => remove(false)}>
                전체 삭제
              </Button>
            </>
          ) : (
            <Button variant="danger" onClick={() => remove(false)}>
              <Icon name="trash" size={16} /> 삭제
            </Button>
          ))}
        <div className="flex-1" />
        <span className="hidden text-xs text-muted sm:inline">Ctrl+Enter 저장</span>
        <Button variant="outline" onClick={onClose}>
          취소
        </Button>
        <Button variant="primary" type="submit">
          저장
        </Button>
      </div>
    </form>
  );
}
