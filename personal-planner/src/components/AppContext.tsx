"use client";

import { createContext, useContext } from "react";
import type { CalendarMode, Item } from "@/lib/types";

export interface AppActions {
  /** 오늘 날짜 키 (자정이 지나면 자동으로 갱신) */
  today: string;
  /** 현재 시각 (분 단위로 갱신) */
  now: Date;
  openNew: (partial?: Partial<Item>) => void;
  openEdit: (item: Item, occurrenceDate?: string) => void;
  goToDate: (date: string, mode?: CalendarMode) => void;
  startFocus: (itemId?: string) => void;
}

export const AppContext = createContext<AppActions | null>(null);

export function useApp(): AppActions {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppContext");
  return ctx;
}

/** 드래그 앤 드롭으로 옮기는 항목의 id를 담는 MIME 타입 */
export const DRAG_TYPE = "application/x-planner-item";

export interface DragPayload {
  id: string;
  /** 반복 항목이라면 끌기 시작한 날짜 */
  from?: string;
  /** 시간 격자에서 블록을 잡은 위치 (블록 상단으로부터 px) */
  offsetY?: number;
}
