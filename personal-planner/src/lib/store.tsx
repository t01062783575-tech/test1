"use client";

import { createContext, useContext, useEffect, useMemo, useReducer, type ReactNode } from "react";
import { todayKey } from "./date";
import type { Category, FocusSession, Habit, Item, PlannerData, Settings } from "./types";

const STORAGE_KEY = "personal-planner:v1";

export const COLORS = [
  "#6366f1", // indigo
  "#0ea5e9", // sky
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#ec4899", // pink
  "#8b5cf6", // violet
  "#64748b", // slate
];

export const uid = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);

const DEFAULT_SETTINGS: Settings = {
  weekStart: 0,
  theme: "system",
  showHolidays: true,
  focusMinutes: 25,
  breakMinutes: 5,
  notifications: false,
};

function initialData(): PlannerData {
  return {
    version: 1,
    items: [],
    categories: [
      { id: "work", name: "업무", color: COLORS[0] },
      { id: "personal", name: "개인", color: COLORS[2] },
      { id: "study", name: "공부", color: COLORS[3] },
      { id: "health", name: "건강", color: COLORS[4] },
    ],
    habits: [],
    focus: [],
    settings: DEFAULT_SETTINGS,
  };
}

/** 가져온 JSON이나 오래된 저장본에 빠진 필드를 채운다. */
export function normalize(raw: unknown): PlannerData {
  const base = initialData();
  if (!raw || typeof raw !== "object") return base;
  const d = raw as Partial<PlannerData>;
  return {
    version: 1,
    items: Array.isArray(d.items) ? d.items.map(normalizeItem) : [],
    categories: Array.isArray(d.categories) ? d.categories : base.categories,
    habits: Array.isArray(d.habits) ? d.habits.map((h) => ({ ...h, log: h.log ?? [] })) : [],
    focus: Array.isArray(d.focus) ? d.focus : [],
    settings: { ...DEFAULT_SETTINGS, ...(d.settings ?? {}) },
  };
}

function normalizeItem(i: Partial<Item>): Item {
  return {
    id: i.id ?? uid(),
    kind: i.kind ?? "task",
    title: i.title ?? "",
    notes: i.notes ?? "",
    date: i.date || undefined,
    start: i.start || undefined,
    end: i.end || undefined,
    done: i.done ?? false,
    doneDates: i.doneDates ?? [],
    skipDates: i.skipDates ?? [],
    priority: i.priority ?? 4,
    categoryId: i.categoryId || undefined,
    tags: i.tags ?? [],
    subtasks: i.subtasks ?? [],
    repeat: i.repeat ?? { freq: "none", interval: 1 },
    reminder: i.reminder,
    createdAt: i.createdAt ?? new Date().toISOString(),
    completedAt: i.completedAt,
  };
}

export function newItem(partial: Partial<Item>): Item {
  return normalizeItem({ ...partial, id: uid(), createdAt: new Date().toISOString() });
}

function load(): PlannerData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? normalize(JSON.parse(raw)) : initialData();
  } catch {
    return initialData();
  }
}

type Action =
  | { type: "replace"; data: PlannerData }
  | { type: "addItem"; item: Item }
  | { type: "updateItem"; id: string; patch: Partial<Item> }
  | { type: "deleteItem"; id: string }
  /** 반복 항목의 특정 날짜 한 번만 삭제 */
  | { type: "skipOccurrence"; id: string; date: string }
  | { type: "toggleDone"; id: string; date?: string }
  | { type: "toggleSubtask"; id: string; subtaskId: string }
  | { type: "upsertCategory"; category: Category }
  | { type: "deleteCategory"; id: string }
  | { type: "upsertHabit"; habit: Habit }
  | { type: "deleteHabit"; id: string }
  | { type: "toggleHabit"; id: string; date: string }
  | { type: "addFocus"; session: FocusSession }
  | { type: "updateSettings"; patch: Partial<Settings> };

function mapItem(data: PlannerData, id: string, fn: (i: Item) => Item): PlannerData {
  return { ...data, items: data.items.map((i) => (i.id === id ? fn(i) : i)) };
}

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function reducer(data: PlannerData, action: Action): PlannerData {
  switch (action.type) {
    case "replace":
      return action.data;
    case "addItem":
      return { ...data, items: [...data.items, action.item] };
    case "updateItem":
      return mapItem(data, action.id, (i) => ({ ...i, ...action.patch }));
    case "deleteItem":
      return {
        ...data,
        items: data.items.filter((i) => i.id !== action.id),
        focus: data.focus.map((f) => (f.itemId === action.id ? { ...f, itemId: undefined } : f)),
      };
    case "skipOccurrence":
      return mapItem(data, action.id, (i) => ({ ...i, skipDates: [...i.skipDates, action.date] }));
    case "toggleDone":
      return mapItem(data, action.id, (i) => {
        if (i.repeat.freq !== "none") {
          const date = action.date ?? i.date ?? todayKey();
          return { ...i, doneDates: toggle(i.doneDates, date) };
        }
        const done = !i.done;
        return { ...i, done, completedAt: done ? new Date().toISOString() : undefined };
      });
    case "toggleSubtask":
      return mapItem(data, action.id, (i) => ({
        ...i,
        subtasks: i.subtasks.map((s) => (s.id === action.subtaskId ? { ...s, done: !s.done } : s)),
      }));
    case "upsertCategory": {
      const exists = data.categories.some((c) => c.id === action.category.id);
      return {
        ...data,
        categories: exists
          ? data.categories.map((c) => (c.id === action.category.id ? action.category : c))
          : [...data.categories, action.category],
      };
    }
    case "deleteCategory":
      return {
        ...data,
        categories: data.categories.filter((c) => c.id !== action.id),
        items: data.items.map((i) => (i.categoryId === action.id ? { ...i, categoryId: undefined } : i)),
      };
    case "upsertHabit": {
      const exists = data.habits.some((h) => h.id === action.habit.id);
      return {
        ...data,
        habits: exists
          ? data.habits.map((h) => (h.id === action.habit.id ? action.habit : h))
          : [...data.habits, action.habit],
      };
    }
    case "deleteHabit":
      return { ...data, habits: data.habits.filter((h) => h.id !== action.id) };
    case "toggleHabit":
      return {
        ...data,
        habits: data.habits.map((h) => (h.id === action.id ? { ...h, log: toggle(h.log, action.date) } : h)),
      };
    case "addFocus":
      return { ...data, focus: [...data.focus, action.session] };
    case "updateSettings":
      return { ...data, settings: { ...data.settings, ...action.patch } };
  }
}

interface StoreValue {
  data: PlannerData;
  dispatch: (a: Action) => void;
  categoryById: Map<string, Category>;
}

const StoreContext = createContext<StoreValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  // 이 컴포넌트는 브라우저에서만 렌더링되므로 초기값을 바로 localStorage에서 읽는다.
  const [data, dispatch] = useReducer(reducer, undefined, load);

  useEffect(() => {
    try {
      const json = JSON.stringify(data);
      // 같은 내용이면 쓰지 않는다 (다른 탭과 storage 이벤트가 핑퐁하지 않도록)
      if (localStorage.getItem(STORAGE_KEY) !== json) localStorage.setItem(STORAGE_KEY, json);
    } catch {
      // 저장 공간이 없거나 막힌 경우: 메모리에서만 동작
    }
  }, [data]);

  // 다른 탭에서 바뀐 내용을 반영
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        try {
          dispatch({ type: "replace", data: normalize(JSON.parse(e.newValue)) });
        } catch {
          // 무시
        }
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const value = useMemo(
    () => ({ data, dispatch, categoryById: new Map(data.categories.map((c) => [c.id, c])) }),
    [data],
  );
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used inside StoreProvider");
  return ctx;
}
