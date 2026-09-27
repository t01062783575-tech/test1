export type ItemKind = "task" | "event";

/** 1 = 매우 중요, 2 = 중요, 3 = 보통, 4 = 없음 */
export type Priority = 1 | 2 | 3 | 4;

export type RepeatFreq =
  | "none"
  | "daily"
  | "weekdays"
  | "weekly"
  | "monthly"
  | "yearly";

export interface Repeat {
  freq: RepeatFreq;
  /** 몇 번째마다 반복할지 (예: 2주마다 → 2) */
  interval: number;
  /** 반복 종료일 (YYYY-MM-DD) */
  until?: string;
}

export interface Subtask {
  id: string;
  title: string;
  done: boolean;
}

export interface Item {
  id: string;
  kind: ItemKind;
  title: string;
  notes: string;
  /** YYYY-MM-DD. 없으면 날짜 미정(수집함) */
  date?: string;
  /** HH:mm. 없으면 종일 */
  start?: string;
  /** HH:mm */
  end?: string;
  /** 반복하지 않는 항목의 완료 여부 */
  done: boolean;
  /** 반복 항목에서 완료 처리한 날짜 목록 */
  doneDates: string[];
  /** 반복 항목에서 건너뛴(삭제한) 날짜 목록 */
  skipDates: string[];
  priority: Priority;
  categoryId?: string;
  tags: string[];
  subtasks: Subtask[];
  repeat: Repeat;
  /** 시작 몇 분 전에 알림 (없으면 알림 없음) */
  reminder?: number;
  createdAt: string;
  completedAt?: string;
}

export interface Category {
  id: string;
  name: string;
  color: string;
}

export interface Habit {
  id: string;
  name: string;
  color: string;
  /** 체크한 날짜 (YYYY-MM-DD) */
  log: string[];
  createdAt: string;
}

export interface FocusSession {
  id: string;
  date: string;
  minutes: number;
  itemId?: string;
}

export type ThemeSetting = "system" | "light" | "dark";

export interface Settings {
  /** 0 = 일요일 시작, 1 = 월요일 시작 */
  weekStart: 0 | 1;
  theme: ThemeSetting;
  showHolidays: boolean;
  focusMinutes: number;
  breakMinutes: number;
  notifications: boolean;
}

export interface PlannerData {
  version: 1;
  items: Item[];
  categories: Category[];
  habits: Habit[];
  focus: FocusSession[];
  settings: Settings;
}

/** 반복 일정을 펼친 한 번의 발생 */
export interface Occurrence {
  item: Item;
  date: string;
  done: boolean;
}

export type View =
  | "today"
  | "calendar"
  | "tasks"
  | "matrix"
  | "habits"
  | "stats";

export type CalendarMode = "month" | "week" | "day";
