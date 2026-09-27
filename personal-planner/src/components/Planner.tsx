"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { WEEKDAYS, addDays, addMonths, fromKey, monthGrid, timeToMin, toKey } from "@/lib/date";
import { holidayName } from "@/lib/holidays";
import { expandRange, occurrencesOn } from "@/lib/recurrence";
import { StoreProvider, newItem, useStore } from "@/lib/store";
import type { CalendarMode, Item, View } from "@/lib/types";
import { AppContext, type AppActions } from "./AppContext";
import { FocusTimer, notify } from "./FocusTimer";
import { ItemModal, type Editing } from "./ItemModal";
import { SearchPalette } from "./SearchPalette";
import { SettingsModal } from "./SettingsModal";
import { Icon } from "./ui";
import { CalendarView } from "./views/CalendarView";
import { HabitsView } from "./views/HabitsView";
import { MatrixView } from "./views/MatrixView";
import { StatsView } from "./views/StatsView";
import { TasksView, type TaskFilter } from "./views/TasksView";
import { TodayView } from "./views/TodayView";

const NAV: { view: View; label: string; icon: Parameters<typeof Icon>[0]["name"] }[] = [
  { view: "today", label: "오늘", icon: "sun" },
  { view: "calendar", label: "캘린더", icon: "calendar" },
  { view: "tasks", label: "할일", icon: "check" },
  { view: "matrix", label: "매트릭스", icon: "grid" },
  { view: "habits", label: "습관", icon: "flame" },
  { view: "stats", label: "통계", icon: "chart" },
];

const VIEW_KEY = "personal-planner:view";

export default function Planner() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  );
}

function readView(): View {
  try {
    const v = localStorage.getItem(VIEW_KEY) as View | null;
    if (v && NAV.some((n) => n.view === v)) return v;
  } catch {
    // 무시
  }
  return "today";
}

function Shell() {
  const { data, dispatch } = useStore();
  const [now, setNow] = useState(() => new Date());
  const today = toKey(now);
  const [view, setViewState] = useState<View>(readView);
  const [cursor, setCursor] = useState(today);
  const [calMode, setCalMode] = useState<CalendarMode>("month");
  const [taskFilter, setTaskFilter] = useState<TaskFilter>({ type: "inbox" });
  const [editing, setEditing] = useState<Editing | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [focus, setFocus] = useState<{ itemId?: string } | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const notified = useRef(new Set<string>());

  const setView = useCallback((v: View) => {
    setViewState(v);
    setNavOpen(false);
    try {
      localStorage.setItem(VIEW_KEY, v);
    } catch {
      // 무시
    }
  }, []);

  // 시계: 30초마다 갱신 (자정이 지나면 "오늘"도 바뀐다)
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  // 테마 적용
  const theme = data.settings.theme;
  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const apply = () =>
      document.documentElement.setAttribute("data-theme", theme === "system" ? (mq.matches ? "dark" : "light") : theme);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme]);

  // 일정 알림 (탭이 열려 있는 동안)
  useEffect(() => {
    if (!data.settings.notifications) return;
    const nowMs = now.getTime();
    const candidates = expandRange(data.items, today, addDays(today, 1));
    for (const [date, list] of candidates) {
      for (const o of list) {
        if (o.done || o.item.reminder === undefined) continue;
        const [y, m, d] = date.split("-").map(Number);
        const startMin = o.item.start ? timeToMin(o.item.start) : 9 * 60;
        const at = new Date(y, m - 1, d, 0, startMin).getTime() - o.item.reminder * 60_000;
        const key = `${o.item.id}:${date}`;
        if (nowMs >= at && nowMs - at < 2 * 60_000 && !notified.current.has(key)) {
          notified.current.add(key);
          notify(o.item.title, o.item.start ? `${o.item.start} 시작` : "오늘 할 일이에요");
        }
      }
    }
  }, [now, data.items, data.settings.notifications, today]);

  const openNew = useCallback(
    (partial?: Partial<Item>) =>
      setEditing({ item: newItem({ kind: partial?.start ? "event" : "task", ...partial }), isNew: true }),
    [],
  );
  const openEdit = useCallback((item: Item, occurrenceDate?: string) => setEditing({ item, isNew: false, occurrenceDate }), []);
  const goToDate = useCallback(
    (date: string, mode?: CalendarMode) => {
      setCursor(date);
      if (mode) setCalMode(mode);
      setView("calendar");
    },
    [setView],
  );
  const startFocus = useCallback((itemId?: string) => setFocus({ itemId }), []);

  const actions = useMemo<AppActions>(
    () => ({ today, now, openNew, openEdit, goToDate, startFocus }),
    [today, now, openNew, openEdit, goToDate, startFocus],
  );

  // 키보드 단축키
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen((v) => !v);
        return;
      }
      const t = e.target as HTMLElement;
      if (e.metaKey || e.ctrlKey || e.altKey || e.isComposing) return;
      if (t.closest("input, textarea, select, [contenteditable=true], [role=dialog]")) return;
      if (editing || searchOpen || settingsOpen) return;
      const k = e.key.toLowerCase();
      const idx = Number(e.key) - 1;
      if (idx >= 0 && idx < NAV.length) setView(NAV[idx].view);
      else if (k === "n") {
        e.preventDefault();
        openNew(view === "calendar" ? { date: cursor } : view === "today" ? { date: today } : undefined);
      } else if (k === "q") {
        const input = document.querySelector<HTMLInputElement>("[data-quickadd] input");
        if (input) {
          e.preventDefault();
          input.focus();
        }
      } else if (k === "f") setFocus((f) => f ?? {});
      else if (view === "calendar") {
        const stepMs = (dir: 1 | -1) =>
          setCursor((c) => (calMode === "month" ? addMonths(c, dir) : addDays(c, calMode === "week" ? 7 * dir : dir)));
        if (e.key === "ArrowLeft") stepMs(-1);
        else if (e.key === "ArrowRight") stepMs(1);
        else if (k === "t") setCursor(today);
        else if (k === "m") setCalMode("month");
        else if (k === "w") setCalMode("week");
        else if (k === "d") setCalMode("day");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editing, searchOpen, settingsOpen, view, cursor, calMode, today, openNew, setView]);

  const inboxCount = data.items.filter((i) => !i.date && !i.done).length;
  const todayCount = occurrencesOn(data.items, today).filter((o) => !o.done && o.item.kind === "task").length;
  const counts: Partial<Record<View, number>> = { today: todayCount, tasks: inboxCount };

  const sidebar = (
    <nav className="flex h-full flex-col gap-4 p-3">
      <div className="flex items-center gap-2 px-2 pt-1">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white">
          <Icon name="check" size={18} />
        </span>
        <span className="text-base font-bold">나의 플래너</span>
      </div>
      <button
        onClick={() => setSearchOpen(true)}
        className="flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-muted hover:text-ink"
      >
        <Icon name="search" size={16} /> 검색
        <kbd className="ml-auto rounded border border-line px-1 text-[10px]">Ctrl K</kbd>
      </button>
      <div className="space-y-0.5">
        {NAV.map((n, i) => (
          <button
            key={n.view}
            onClick={() => setView(n.view)}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm ${
              view === n.view ? "bg-accent-soft font-semibold text-accent" : "hover:bg-surface-2"
            }`}
            title={`단축키 ${i + 1}`}
          >
            <Icon name={n.icon} size={18} />
            {n.label}
            {!!counts[n.view] && <span className="ml-auto text-xs text-muted">{counts[n.view]}</span>}
          </button>
        ))}
      </div>
      <MiniMonth cursor={view === "calendar" ? cursor : today} today={today} onPick={(d) => goToDate(d, calMode === "month" ? "day" : calMode)} />
      <div>
        <div className="mb-1 px-3 text-xs font-semibold text-muted">카테고리</div>
        {data.categories.map((c) => (
          <button
            key={c.id}
            onClick={() => {
              setTaskFilter({ type: "category", id: c.id });
              setView("tasks");
            }}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-1.5 text-sm hover:bg-surface-2"
          >
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
            {c.name}
            <span className="ml-auto text-xs text-muted">
              {data.items.filter((i) => i.categoryId === c.id && i.kind === "task" && !i.done && i.repeat.freq === "none").length || ""}
            </span>
          </button>
        ))}
      </div>
      <div className="mt-auto flex items-center gap-1 border-t border-line pt-3">
        <button onClick={() => setFocus((f) => f ?? {})} className="flex flex-1 items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-surface-2">
          <Icon name="timer" size={18} /> 집중 타이머
        </button>
        <button
          onClick={() => {
            const isDark = document.documentElement.getAttribute("data-theme") === "dark";
            dispatch({ type: "updateSettings", patch: { theme: isDark ? "light" : "dark" } });
          }}
          className="rounded-lg p-2 hover:bg-surface-2"
          title="라이트/다크 전환"
        >
          <Icon name="moon" size={18} className="dark:hidden" />
          <Icon name="sun" size={18} className="hidden dark:block" />
        </button>
        <button onClick={() => setSettingsOpen(true)} className="rounded-lg p-2 hover:bg-surface-2" title="설정">
          <Icon name="settings" size={18} />
        </button>
      </div>
    </nav>
  );

  return (
    <AppContext.Provider value={actions}>
      <div className="flex h-dvh overflow-hidden">
        <aside className="scroll-thin hidden w-64 shrink-0 overflow-y-auto border-r border-line bg-surface md:block">{sidebar}</aside>
        {navOpen && (
          <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={() => setNavOpen(false)}>
            <aside className="scroll-thin h-full w-72 overflow-y-auto bg-surface" onClick={(e) => e.stopPropagation()}>
              {sidebar}
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          {/* 모바일 상단 바 */}
          <header className="flex items-center gap-2 border-b border-line bg-surface px-3 py-2 md:hidden">
            <button onClick={() => setNavOpen(true)} className="rounded-lg p-1.5 hover:bg-surface-2" aria-label="메뉴">
              <Icon name="menu" />
            </button>
            <span className="font-bold">{NAV.find((n) => n.view === view)?.label}</span>
            <div className="flex-1" />
            <button onClick={() => setSearchOpen(true)} className="rounded-lg p-1.5 hover:bg-surface-2" aria-label="검색">
              <Icon name="search" />
            </button>
            <button onClick={() => setSettingsOpen(true)} className="rounded-lg p-1.5 hover:bg-surface-2" aria-label="설정">
              <Icon name="settings" />
            </button>
          </header>

          <main className={`scroll-thin min-h-0 flex-1 pb-16 md:pb-0 ${view === "calendar" ? "overflow-hidden" : "overflow-y-auto"}`}>
            {view === "today" && <TodayView />}
            {view === "calendar" && <CalendarView cursor={cursor} mode={calMode} onCursor={setCursor} onMode={setCalMode} />}
            {view === "tasks" && <TasksView filter={taskFilter} onFilter={setTaskFilter} />}
            {view === "matrix" && <MatrixView />}
            {view === "habits" && <HabitsView />}
            {view === "stats" && <StatsView />}
          </main>

          {/* 모바일 하단 탭 */}
          <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-surface md:hidden">
            {NAV.slice(0, 5).map((n) => (
              <button
                key={n.view}
                onClick={() => setView(n.view)}
                className={`flex flex-col items-center gap-0.5 py-2 text-[10px] ${view === n.view ? "text-accent" : "text-muted"}`}
              >
                <Icon name={n.icon} size={20} />
                {n.label}
              </button>
            ))}
          </nav>
        </div>

        {/* 새 항목 버튼 */}
        <button
          onClick={() => openNew(view === "calendar" ? { date: cursor } : view === "today" ? { date: today } : undefined)}
          className="fixed right-4 bottom-20 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-white shadow-lg hover:opacity-90 md:hidden"
          style={focus ? { display: "none" } : undefined}
          aria-label="새 항목"
        >
          <Icon name="plus" size={22} />
        </button>
      </div>

      <ItemModal editing={editing} onClose={() => setEditing(null)} />
      <SearchPalette open={searchOpen} onClose={() => setSearchOpen(false)} onView={setView} />
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      {focus && (
        <FocusTimer itemId={focus.itemId} onItemChange={(itemId) => setFocus({ itemId })} onClose={() => setFocus(null)} />
      )}
    </AppContext.Provider>
  );
}

function MiniMonth({ cursor, today, onPick }: { cursor: string; today: string; onPick: (d: string) => void }) {
  const { data } = useStore();
  const [month, setMonth] = useState(cursor.slice(0, 7) + "-01");
  const [lastCursor, setLastCursor] = useState(cursor);
  // 바깥에서 커서가 바뀌면 그 달로 따라간다
  if (cursor !== lastCursor) {
    setLastCursor(cursor);
    setMonth(cursor.slice(0, 7) + "-01");
  }
  const days = monthGrid(month, data.settings.weekStart);
  const occ = expandRange(data.items, days[0], days[41]);
  const d = fromKey(month);

  return (
    <div className="px-1">
      <div className="mb-1 flex items-center justify-between px-2">
        <span className="text-sm font-semibold">
          {d.getFullYear()}년 {d.getMonth() + 1}월
        </span>
        <div className="flex">
          <button onClick={() => setMonth(addMonths(month, -1))} className="rounded p-0.5 hover:bg-surface-2" aria-label="이전 달">
            <Icon name="left" size={16} />
          </button>
          <button onClick={() => setMonth(addMonths(month, 1))} className="rounded p-0.5 hover:bg-surface-2" aria-label="다음 달">
            <Icon name="right" size={16} />
          </button>
        </div>
      </div>
      <div className="grid grid-cols-7 text-center text-[10px] text-muted">
        {Array.from({ length: 7 }, (_, i) => (i + data.settings.weekStart) % 7).map((wd) => (
          <div key={wd} className="py-1">
            {WEEKDAYS[wd]}
          </div>
        ))}
        {days.map((day) => {
          const wd = fromKey(day).getDay();
          const holiday = data.settings.showHolidays && holidayName(day);
          const has = (occ.get(day) ?? []).some((o) => !o.done);
          return (
            <button
              key={day}
              onClick={() => onPick(day)}
              title={holiday || undefined}
              className={`relative mx-auto flex h-7 w-7 items-center justify-center rounded-full text-xs ${
                day === today
                  ? "bg-accent font-semibold text-white"
                  : day === cursor
                    ? "bg-accent-soft font-semibold text-accent"
                    : `hover:bg-surface-2 ${holiday || wd === 0 ? "text-holiday" : wd === 6 ? "text-saturday" : "text-ink"}`
              } ${day.slice(0, 7) === month.slice(0, 7) ? "" : "opacity-35"}`}
            >
              {fromKey(day).getDate()}
              {has && day !== today && <span className="absolute bottom-0.5 h-1 w-1 rounded-full bg-accent" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
