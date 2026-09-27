"use client";

import { useEffect, useRef, useState, type DragEvent, type MouseEvent } from "react";
import {
  WEEKDAYS,
  addDays,
  addMonths,
  formatTime,
  fromKey,
  minToTime,
  monthGrid,
  rangeKeys,
  startOfWeek,
  timeToMin,
  weekday,
} from "@/lib/date";
import { holidayName } from "@/lib/holidays";
import { expandRange } from "@/lib/recurrence";
import { newItem, useStore } from "@/lib/store";
import type { CalendarMode, Occurrence } from "@/lib/types";
import { DRAG_TYPE, useApp, type DragPayload } from "../AppContext";
import { ItemRow } from "../ItemRow";
import { Icon } from "../ui";

const HOUR_PX = 48;

function readPayload(e: DragEvent): DragPayload | null {
  try {
    const raw = e.dataTransfer.getData(DRAG_TYPE);
    return raw ? (JSON.parse(raw) as DragPayload) : null;
  } catch {
    return null;
  }
}

function acceptDrag(e: DragEvent) {
  if (e.dataTransfer.types.includes(DRAG_TYPE)) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }
}

/** 항목을 다른 날짜(와 시간)로 옮긴다. 반복 항목은 그 회차만 떼어내서 옮긴다. */
function useMoveItem() {
  const { data, dispatch } = useStore();
  return (payload: DragPayload, date: string, start?: string | null) => {
    const item = data.items.find((i) => i.id === payload.id);
    if (!item) return;
    const patch: { date: string; start?: string; end?: string } = { date };
    if (start === null) {
      patch.start = undefined;
      patch.end = undefined;
    } else if (start) {
      const len = item.start && item.end ? timeToMin(item.end) - timeToMin(item.start) : 60;
      patch.start = start;
      patch.end = minToTime(timeToMin(start) + Math.max(15, len));
    }
    if (item.repeat.freq !== "none" && payload.from) {
      dispatch({ type: "skipOccurrence", id: item.id, date: payload.from });
      dispatch({
        type: "addItem",
        item: newItem({
          ...item,
          ...patch,
          repeat: { freq: "none", interval: 1 },
          doneDates: [],
          skipDates: [],
          done: item.doneDates.includes(payload.from),
        }),
      });
    } else {
      dispatch({ type: "updateItem", id: item.id, patch });
    }
  };
}

export function CalendarView({
  cursor,
  mode,
  onCursor,
  onMode,
}: {
  cursor: string;
  mode: CalendarMode;
  onCursor: (d: string) => void;
  onMode: (m: CalendarMode) => void;
}) {
  const { data } = useStore();
  const { today } = useApp();
  const [showInbox, setShowInbox] = useState(true);
  const weekStart = data.settings.weekStart;

  const step = (dir: 1 | -1) => {
    if (mode === "month") onCursor(addMonths(cursor, dir));
    else if (mode === "week") onCursor(addDays(cursor, 7 * dir));
    else onCursor(addDays(cursor, dir));
  };

  const d = fromKey(cursor);
  let title = `${d.getFullYear()}년 ${d.getMonth() + 1}월`;
  if (mode === "week") {
    const s = startOfWeek(cursor, weekStart);
    const e = addDays(s, 6);
    const sd = fromKey(s);
    const ed = fromKey(e);
    title =
      sd.getMonth() === ed.getMonth()
        ? `${sd.getFullYear()}년 ${sd.getMonth() + 1}월 ${sd.getDate()}–${ed.getDate()}일`
        : `${sd.getMonth() + 1}월 ${sd.getDate()}일 – ${ed.getMonth() + 1}월 ${ed.getDate()}일`;
  } else if (mode === "day") {
    title = `${d.getMonth() + 1}월 ${d.getDate()}일 ${WEEKDAYS[d.getDay()]}요일`;
  }

  const inbox = data.items.filter((i) => !i.date && !i.done);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-3">
        <h1 className="mr-2 text-lg font-bold">{title}</h1>
        <div className="flex items-center">
          <button onClick={() => step(-1)} className="rounded-lg p-1.5 hover:bg-surface-2" aria-label="이전">
            <Icon name="left" />
          </button>
          <button onClick={() => onCursor(today)} className="rounded-lg border border-line px-2.5 py-1 text-sm hover:bg-surface-2">
            오늘
          </button>
          <button onClick={() => step(1)} className="rounded-lg p-1.5 hover:bg-surface-2" aria-label="다음">
            <Icon name="right" />
          </button>
        </div>
        <div className="flex-1" />
        <div className="flex rounded-lg bg-surface-2 p-0.5 text-sm">
          {(["month", "week", "day"] as const).map((m) => (
            <button
              key={m}
              onClick={() => onMode(m)}
              className={`rounded-md px-3 py-1 ${mode === m ? "bg-surface font-semibold shadow-sm" : "text-muted"}`}
            >
              {{ month: "월", week: "주", day: "일" }[m]}
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowInbox((v) => !v)}
          className={`hidden rounded-lg p-1.5 lg:block ${showInbox ? "bg-accent-soft text-accent" : "hover:bg-surface-2"}`}
          title="날짜 없는 할일 패널"
        >
          <Icon name="inbox" />
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          {mode === "month" ? (
            <MonthGrid cursor={cursor} onDay={(day) => { onCursor(day); onMode("day"); }} />
          ) : (
            <TimeGrid days={mode === "week" ? rangeKeys(startOfWeek(cursor, weekStart), 7) : [cursor]} onDay={(day) => { onCursor(day); onMode("day"); }} />
          )}
        </div>
        {showInbox && (
          <aside className="scroll-thin hidden w-72 shrink-0 overflow-y-auto border-l border-line p-3 lg:block">
            <h2 className="px-2 text-sm font-semibold">날짜 없는 할일</h2>
            <p className="mb-2 px-2 text-xs text-muted">캘린더로 끌어다 놓으면 일정이 잡혀요.</p>
            {inbox.length === 0 && <p className="px-2 py-4 text-sm text-muted">비어 있어요.</p>}
            {inbox.map((i) => (
              <ItemRow key={i.id} item={i} compact />
            ))}
          </aside>
        )}
      </div>
    </div>
  );
}

function MonthGrid({ cursor, onDay }: { cursor: string; onDay: (d: string) => void }) {
  const { data, categoryById } = useStore();
  const { today, openNew, openEdit } = useApp();
  const move = useMoveItem();
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const weekStart = data.settings.weekStart;
  const days = monthGrid(cursor, weekStart);
  const occ = expandRange(data.items, days[0], days[41]);
  const month = cursor.slice(0, 7);

  return (
    <div className="flex h-full flex-col">
      <div className="grid grid-cols-7 border-b border-line text-center text-xs text-muted">
        {Array.from({ length: 7 }, (_, i) => (i + weekStart) % 7).map((wd) => (
          <div key={wd} className={`py-2 ${wd === 0 ? "text-holiday" : wd === 6 ? "text-saturday" : ""}`}>
            {WEEKDAYS[wd]}
          </div>
        ))}
      </div>
      <div className="grid flex-1 grid-cols-7 grid-rows-6">
        {days.map((day) => {
          const list = occ.get(day) ?? [];
          const wd = weekday(day);
          const holiday = data.settings.showHolidays ? holidayName(day) : undefined;
          const inMonth = day.startsWith(month);
          const isToday = day === today;
          const dateColor = holiday || wd === 0 ? "text-holiday" : wd === 6 ? "text-saturday" : "";
          return (
            <div
              key={day}
              onClick={() => openNew({ date: day })}
              onDragOver={(e) => {
                acceptDrag(e);
                setDropTarget(day);
              }}
              onDragLeave={() => setDropTarget((t) => (t === day ? null : t))}
              onDrop={(e) => {
                e.preventDefault();
                setDropTarget(null);
                const p = readPayload(e);
                if (p) move(p, day);
              }}
              className={`min-h-[84px] cursor-pointer overflow-hidden border-r border-b border-line p-1 sm:min-h-[104px] ${
                inMonth ? "" : "bg-surface-2/50"
              } ${dropTarget === day ? "bg-accent-soft" : "hover:bg-surface-2/60"}`}
            >
              <div className="mb-0.5 flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDay(day);
                  }}
                  className={`flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-xs font-medium ${
                    isToday ? "bg-accent text-white" : `${dateColor} hover:bg-surface-2`
                  } ${inMonth ? "" : "opacity-40"}`}
                >
                  {fromKey(day).getDate()}
                </button>
                {holiday && <span className="truncate text-[10px] text-holiday">{holiday}</span>}
              </div>
              <div className="space-y-0.5">
                {list.slice(0, 3).map((o) => (
                  <MonthChip
                    key={o.item.id + o.date}
                    o={o}
                    color={(o.item.categoryId && categoryById.get(o.item.categoryId)?.color) || "var(--accent)"}
                    onClick={() => openEdit(o.item, o.date)}
                  />
                ))}
                {list.length > 3 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDay(day);
                    }}
                    className="px-1 text-[11px] text-muted hover:text-ink"
                  >
                    +{list.length - 3}개 더보기
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MonthChip({ o, color, onClick }: { o: Occurrence; color: string; onClick: () => void }) {
  const timed = !!o.item.start;
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.stopPropagation();
        const payload: DragPayload = { id: o.item.id, from: o.date };
        e.dataTransfer.setData(DRAG_TYPE, JSON.stringify(payload));
      }}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      title={o.item.title}
      className={`flex items-center gap-1 truncate rounded px-1 py-px text-[11px] leading-4 ${o.done ? "line-through opacity-50" : ""}`}
      style={timed ? undefined : { background: `color-mix(in srgb, ${color} 18%, transparent)` }}
    >
      {timed ? (
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: color }} />
      ) : o.item.kind === "task" ? (
        <span className="h-2 w-2 shrink-0 rounded-sm border" style={{ borderColor: color, background: o.done ? color : "transparent" }} />
      ) : null}
      {timed && <span className="hidden text-muted sm:inline">{o.item.start}</span>}
      <span className="truncate">{o.item.title}</span>
    </div>
  );
}

interface Placed {
  o: Occurrence;
  top: number;
  height: number;
  col: number;
  cols: number;
}

/** 겹치는 일정을 나란히 배치한다. */
function layout(list: Occurrence[]): Placed[] {
  const timed = list
    .filter((o) => o.item.start)
    .map((o) => {
      const s = timeToMin(o.item.start!);
      const e = o.item.end ? Math.max(timeToMin(o.item.end), s + 15) : s + 30;
      return { o, s, e };
    })
    .sort((a, b) => a.s - b.s || b.e - a.e);
  const placed: Placed[] = [];
  let cluster: { o: Occurrence; s: number; e: number; col: number }[] = [];
  let clusterEnd = -1;
  const flush = () => {
    const cols = Math.max(0, ...cluster.map((c) => c.col)) + 1;
    for (const c of cluster) {
      placed.push({ o: c.o, top: (c.s / 60) * HOUR_PX, height: Math.max(18, ((c.e - c.s) / 60) * HOUR_PX - 2), col: c.col, cols });
    }
    cluster = [];
  };
  for (const t of timed) {
    if (t.s >= clusterEnd && cluster.length) flush();
    const used = new Set(cluster.filter((c) => c.e > t.s).map((c) => c.col));
    let col = 0;
    while (used.has(col)) col++;
    cluster.push({ ...t, col });
    clusterEnd = Math.max(clusterEnd, t.e);
  }
  if (cluster.length) flush();
  return placed;
}

function TimeGrid({ days, onDay }: { days: string[]; onDay: (d: string) => void }) {
  const { data, dispatch, categoryById } = useStore();
  const { today, now, openNew, openEdit } = useApp();
  const move = useMoveItem();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<{ day: string; min: number } | null>(null);
  const occ = expandRange(data.items, days[0], days[days.length - 1]);
  const nowMin = now.getHours() * 60 + now.getMinutes();

  // 보는 날짜가 바뀌면 첫 일정과 지금 시각 중 이른 쪽(없으면 오전 8시) 근처로 스크롤
  const firstStart = Math.min(
    ...days.flatMap((d) => (occ.get(d) ?? []).filter((o) => o.item.start).map((o) => timeToMin(o.item.start!) / 60)),
    days.includes(today) ? now.getHours() : 8,
  );
  const rangeKey = `${days[0]}:${days.length}`;
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = Math.max(0, (Math.min(firstStart, 20) - 1) * HOUR_PX);
    // 날짜 범위가 바뀔 때만 스크롤한다 (일정을 옮길 때마다 튀지 않도록)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rangeKey]);

  const minFromEvent = (e: DragEvent | MouseEvent, offsetY = 0) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const raw = ((e.clientY - rect.top - offsetY) / HOUR_PX) * 60;
    return Math.max(0, Math.min(24 * 60 - 15, Math.round(raw / 15) * 15));
  };

  const colorOf = (o: Occurrence) => (o.item.categoryId && categoryById.get(o.item.categoryId)?.color) || "var(--accent)";

  return (
    <div className="flex h-full flex-col">
      {/* 요일 헤더 + 종일 영역 */}
      <div className="flex border-b border-line">
        <div className="w-12 shrink-0 pt-9 text-right text-[10px] text-muted sm:w-14">
          <span className="pr-1">종일</span>
        </div>
        {days.map((day) => {
          const wd = weekday(day);
          const holiday = data.settings.showHolidays ? holidayName(day) : undefined;
          const allDay = (occ.get(day) ?? []).filter((o) => !o.item.start);
          return (
            <div
              key={day}
              className="min-w-0 flex-1 border-l border-line"
              onDragOver={acceptDrag}
              onDrop={(e) => {
                e.preventDefault();
                const p = readPayload(e);
                if (p) move(p, day, null);
              }}
            >
              <button onClick={() => onDay(day)} className="flex w-full items-baseline justify-center gap-1 py-1.5">
                <span className={`text-xs ${holiday || wd === 0 ? "text-holiday" : wd === 6 ? "text-saturday" : "text-muted"}`}>
                  {WEEKDAYS[wd]}
                </span>
                <span
                  className={`flex h-7 min-w-7 items-center justify-center rounded-full text-sm font-semibold ${
                    day === today ? "bg-accent text-white" : ""
                  }`}
                >
                  {fromKey(day).getDate()}
                </span>
              </button>
              {holiday && <div className="truncate px-1 text-center text-[10px] text-holiday">{holiday}</div>}
              <div className="min-h-7 space-y-0.5 p-1" onClick={() => openNew({ date: day })}>
                {allDay.map((o) => (
                  <div
                    key={o.item.id + o.date}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData(DRAG_TYPE, JSON.stringify({ id: o.item.id, from: o.date }))}
                    onClick={(e) => {
                      e.stopPropagation();
                      openEdit(o.item, o.date);
                    }}
                    className="flex cursor-pointer items-center gap-1 truncate rounded px-1.5 py-0.5 text-[11px]"
                    style={{ background: `color-mix(in srgb, ${colorOf(o)} 18%, transparent)` }}
                  >
                    {o.item.kind === "task" && (
                      <input
                        type="checkbox"
                        checked={o.done}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => dispatch({ type: "toggleDone", id: o.item.id, date: o.date })}
                        className="h-3 w-3 accent-[var(--accent)]"
                      />
                    )}
                    <span className={`truncate ${o.done ? "line-through opacity-60" : ""}`}>{o.item.title}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* 시간 격자 */}
      <div ref={scrollRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        <div className="relative flex" style={{ height: HOUR_PX * 24 }}>
          <div className="w-12 shrink-0 sm:w-14">
            {Array.from({ length: 24 }, (_, h) => (
              <div key={h} className="relative text-right text-[10px] text-muted" style={{ height: HOUR_PX }}>
                {h > 0 && <span className="absolute -top-2 right-1.5">{h < 12 ? `오전 ${h}` : h === 12 ? "오후 12" : `오후 ${h - 12}`}</span>}
              </div>
            ))}
          </div>
          {days.map((day) => {
            const placed = layout(occ.get(day) ?? []);
            return (
              <div
                key={day}
                className="relative min-w-0 flex-1 border-l border-line"
                style={{
                  backgroundImage: `repeating-linear-gradient(to bottom, var(--line) 0, var(--line) 1px, transparent 1px, transparent ${HOUR_PX}px)`,
                }}
                onClick={(e) => {
                  const start = Math.floor(minFromEvent(e) / 30) * 30;
                  openNew({ kind: "event", date: day, start: minToTime(start), end: minToTime(start + 60) });
                }}
                onDragOver={(e) => {
                  acceptDrag(e);
                  setHover({ day, min: minFromEvent(e) });
                }}
                onDragLeave={() => setHover(null)}
                onDrop={(e) => {
                  e.preventDefault();
                  setHover(null);
                  const p = readPayload(e);
                  if (p) move(p, day, minToTime(minFromEvent(e, p.offsetY ?? 0)));
                }}
              >
                {hover?.day === day && (
                  <div className="pointer-events-none absolute inset-x-1 h-0.5 rounded bg-accent" style={{ top: (hover.min / 60) * HOUR_PX }} />
                )}
                {day === today && (
                  <div className="pointer-events-none absolute inset-x-0 z-10 flex items-center" style={{ top: (nowMin / 60) * HOUR_PX }}>
                    <span className="-ml-1 h-2 w-2 rounded-full bg-danger" />
                    <span className="h-0.5 flex-1 bg-danger" />
                  </div>
                )}
                {placed.map(({ o, top, height, col, cols }) => {
                  const color = colorOf(o);
                  return (
                    <div
                      key={o.item.id + o.date}
                      draggable
                      onDragStart={(e) => {
                        const payload: DragPayload = {
                          id: o.item.id,
                          from: o.date,
                          offsetY: e.clientY - e.currentTarget.getBoundingClientRect().top,
                        };
                        e.dataTransfer.setData(DRAG_TYPE, JSON.stringify(payload));
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        openEdit(o.item, o.date);
                      }}
                      className={`absolute cursor-pointer overflow-hidden rounded-md border-l-[3px] px-1.5 py-0.5 text-[11px] leading-tight ${o.done ? "opacity-50" : ""}`}
                      style={{
                        top,
                        height,
                        left: `calc(${(col / cols) * 100}% + 2px)`,
                        width: `calc(${100 / cols}% - 4px)`,
                        borderColor: color,
                        background: `color-mix(in srgb, ${color} 18%, var(--surface))`,
                      }}
                    >
                      <div className={`truncate font-semibold ${o.done ? "line-through" : ""}`}>
                        {o.item.kind === "task" && (o.done ? "☑ " : "☐ ")}
                        {o.item.title}
                      </div>
                      {height > 30 && (
                        <div className="truncate text-muted">
                          {formatTime(o.item.start!)}
                          {o.item.end && ` ~ ${formatTime(o.item.end)}`}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
