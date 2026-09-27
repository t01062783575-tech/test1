// 모든 날짜는 로컬 시간 기준 "YYYY-MM-DD" 문자열로 다룬다.

export const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const pad = (n: number) => String(n).padStart(2, "0");

export function toKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function fromKey(key: string): Date {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function todayKey(): string {
  return toKey(new Date());
}

export function addDays(key: string, n: number): string {
  const d = fromKey(key);
  d.setDate(d.getDate() + n);
  return toKey(d);
}

/** 월 단위 이동. 말일이 없으면 그 달의 마지막 날로 맞춘다. */
export function addMonths(key: string, n: number): string {
  const d = fromKey(key);
  const day = d.getDate();
  d.setDate(1);
  d.setMonth(d.getMonth() + n);
  d.setDate(Math.min(day, daysInMonth(d.getFullYear(), d.getMonth())));
  return toKey(d);
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

export function diffDays(a: string, b: string): number {
  return Math.round((fromKey(b).getTime() - fromKey(a).getTime()) / 86400000);
}

export function weekday(key: string): number {
  return fromKey(key).getDay();
}

export function startOfWeek(key: string, weekStart: 0 | 1): string {
  const wd = weekday(key);
  return addDays(key, -((wd - weekStart + 7) % 7));
}

export function startOfMonth(key: string): string {
  return key.slice(0, 8) + "01";
}

export function rangeKeys(start: string, days: number): string[] {
  return Array.from({ length: days }, (_, i) => addDays(start, i));
}

/** 월 달력용 6주(42일) 격자 */
export function monthGrid(key: string, weekStart: 0 | 1): string[] {
  return rangeKeys(startOfWeek(startOfMonth(key), weekStart), 42);
}

export function timeToMin(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

export function minToTime(min: number): string {
  const clamped = Math.max(0, Math.min(24 * 60 - 1, min));
  return `${pad(Math.floor(clamped / 60))}:${pad(clamped % 60)}`;
}

export function formatTime(t: string): string {
  const [h, m] = t.split(":").map(Number);
  const ap = h < 12 ? "오전" : "오후";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${ap} ${h12}시${m ? ` ${m}분` : ""}`;
}

export function formatDate(key: string, withYear = false): string {
  const d = fromKey(key);
  const base = `${d.getMonth() + 1}월 ${d.getDate()}일 (${WEEKDAYS[d.getDay()]})`;
  return withYear ? `${d.getFullYear()}년 ${base}` : base;
}

/** "오늘", "내일", "어제", 그 외는 날짜 */
export function relativeLabel(key: string, today: string): string {
  const diff = diffDays(today, key);
  if (diff === 0) return "오늘";
  if (diff === 1) return "내일";
  if (diff === 2) return "모레";
  if (diff === -1) return "어제";
  return formatDate(key, key.slice(0, 4) !== today.slice(0, 4));
}
