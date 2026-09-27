import { addDays, diffDays, fromKey, weekday } from "./date";
import type { Item, Occurrence, Repeat } from "./types";

export const REPEAT_LABEL: Record<Repeat["freq"], string> = {
  none: "반복 안 함",
  daily: "매일",
  weekdays: "평일마다",
  weekly: "매주",
  monthly: "매월",
  yearly: "매년",
};

export function repeatText(r: Repeat): string {
  if (r.freq === "none") return "";
  if (r.interval > 1) {
    const unit = { daily: "일", weekdays: "평일", weekly: "주", monthly: "개월", yearly: "년" }[r.freq];
    return `${r.interval}${unit}마다`;
  }
  return REPEAT_LABEL[r.freq];
}

/** start 날짜에서 시작한 반복 규칙이 key 날짜에 발생하는지 */
export function occursOn(start: string, r: Repeat, key: string): boolean {
  if (key < start) return false;
  if (r.until && key > r.until) return false;
  const interval = Math.max(1, r.interval);
  const s = fromKey(start);
  const d = fromKey(key);
  switch (r.freq) {
    case "none":
      return key === start;
    case "daily":
      return diffDays(start, key) % interval === 0;
    case "weekdays": {
      const wd = weekday(key);
      return wd !== 0 && wd !== 6;
    }
    case "weekly":
      return diffDays(start, key) % (7 * interval) === 0;
    case "monthly": {
      const months = (d.getFullYear() - s.getFullYear()) * 12 + d.getMonth() - s.getMonth();
      return months % interval === 0 && d.getDate() === s.getDate();
    }
    case "yearly":
      return (
        (d.getFullYear() - s.getFullYear()) % interval === 0 &&
        d.getMonth() === s.getMonth() &&
        d.getDate() === s.getDate()
      );
  }
}

export function isOccurrenceDone(item: Item, date: string): boolean {
  return item.repeat.freq === "none" ? item.done : item.doneDates.includes(date);
}

/** [from, to] 범위(양 끝 포함) 안의 모든 발생을 날짜별로 모은다. */
export function expandRange(items: Item[], from: string, to: string): Map<string, Occurrence[]> {
  const map = new Map<string, Occurrence[]>();
  const push = (o: Occurrence) => {
    const list = map.get(o.date);
    if (list) list.push(o);
    else map.set(o.date, [o]);
  };
  for (const item of items) {
    if (!item.date) continue;
    if (item.repeat.freq === "none") {
      if (item.date >= from && item.date <= to) push({ item, date: item.date, done: item.done });
      continue;
    }
    let key = item.date > from ? item.date : from;
    while (key <= to) {
      if (occursOn(item.date, item.repeat, key) && !item.skipDates.includes(key)) {
        push({ item, date: key, done: item.doneDates.includes(key) });
      }
      key = addDays(key, 1);
    }
  }
  for (const list of map.values()) list.sort(compareOccurrences);
  return map;
}

export function occurrencesOn(items: Item[], key: string): Occurrence[] {
  return expandRange(items, key, key).get(key) ?? [];
}

/** 종일 → 시간순 → 우선순위 → 제목 */
export function compareOccurrences(a: Occurrence, b: Occurrence): number {
  if (a.done !== b.done) return a.done ? 1 : -1;
  const at = a.item.start ?? "";
  const bt = b.item.start ?? "";
  if (at !== bt) return at < bt ? -1 : 1;
  if (a.item.priority !== b.item.priority) return a.item.priority - b.item.priority;
  return a.item.title.localeCompare(b.item.title, "ko");
}

/** 반복 항목의 key 이후(포함) 다음 발생일. 최대 2년까지만 찾는다. */
export function nextOccurrence(item: Item, key: string): string | undefined {
  if (!item.date) return undefined;
  if (item.repeat.freq === "none") return item.date >= key ? item.date : undefined;
  let k = item.date > key ? item.date : key;
  for (let i = 0; i < 366 * 2; i++) {
    if (occursOn(item.date, item.repeat, k) && !item.skipDates.includes(k) && !item.doneDates.includes(k)) {
      return k;
    }
    k = addDays(k, 1);
  }
  return undefined;
}
