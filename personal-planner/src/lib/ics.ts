import { addDays } from "./date";
import type { Item } from "./types";

const RRULE: Partial<Record<Item["repeat"]["freq"], string>> = {
  daily: "FREQ=DAILY",
  weekdays: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
  weekly: "FREQ=WEEKLY",
  monthly: "FREQ=MONTHLY",
  yearly: "FREQ=YEARLY",
};

const escape = (s: string) => s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\n/g, "\\n");
const compactDate = (key: string) => key.replace(/-/g, "");
const compactDateTime = (key: string, time: string) => `${compactDate(key)}T${time.replace(":", "")}00`;

/** 구글 캘린더·애플 캘린더 등으로 가져갈 수 있는 .ics 파일 내용 */
export function toICS(items: Item[]): string {
  const now = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//personal-planner//KO", "CALSCALE:GREGORIAN"];
  for (const item of items) {
    if (!item.date) continue;
    const isTask = item.kind === "task";
    lines.push(isTask ? "BEGIN:VTODO" : "BEGIN:VEVENT");
    lines.push(`UID:${item.id}@personal-planner`, `DTSTAMP:${now}`, `SUMMARY:${escape(item.title)}`);
    if (item.notes) lines.push(`DESCRIPTION:${escape(item.notes)}`);
    if (item.start) {
      lines.push(`DTSTART:${compactDateTime(item.date, item.start)}`);
      if (!isTask && item.end) lines.push(`DTEND:${compactDateTime(item.date, item.end)}`);
    } else {
      lines.push(`DTSTART;VALUE=DATE:${compactDate(item.date)}`);
      if (!isTask) lines.push(`DTEND;VALUE=DATE:${compactDate(addDays(item.date, 1))}`);
    }
    if (isTask) lines.push(`STATUS:${item.done ? "COMPLETED" : "NEEDS-ACTION"}`);
    const rule = RRULE[item.repeat.freq];
    if (rule) {
      let r = rule;
      if (item.repeat.interval > 1) r += `;INTERVAL=${item.repeat.interval}`;
      if (item.repeat.until) r += `;UNTIL=${compactDate(item.repeat.until)}`;
      lines.push(`RRULE:${r}`);
    }
    if (item.tags.length) lines.push(`CATEGORIES:${item.tags.map(escape).join(",")}`);
    lines.push(isTask ? "END:VTODO" : "END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  return lines.join("\r\n");
}

export function download(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
