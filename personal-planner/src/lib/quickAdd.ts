import { addDays, addMonths, daysInMonth, fromKey, minToTime, startOfWeek, timeToMin, toKey, weekday } from "./date";
import type { Category, Item, Priority, Repeat } from "./types";

/**
 * 자연어 빠른 추가 파서.
 * 예) "내일 오후 3시~5시 팀 회의 #업무 !1"
 *     "매주 월요일 9시 주간 보고 @회사"
 *     "3일 후 보고서 제출 !!"
 */
export interface ParsedQuickAdd {
  title: string;
  date?: string;
  start?: string;
  end?: string;
  priority: Priority;
  tags: string[];
  categoryId?: string;
  repeat: Repeat;
  kind: Item["kind"];
}

const WD = "일월화수목금토";
const PARTICLE = "(?:에|에는|까지|부터|날)?";
const END = "(?=\\s|$|[,.])";
const MERIDIEM = "(오전|오후|아침|점심|저녁|밤|낮|새벽)";
const TIME = `${MERIDIEM}?\\s*(\\d{1,2})(?:\\s*:\\s*(\\d{2})|\\s*시(?:\\s*(\\d{1,2})\\s*분|\\s*(반))?)`;

function toHour(h: number, meridiem: string | undefined, colon: boolean): number {
  switch (meridiem) {
    case "오후":
    case "저녁":
    case "밤":
      return h < 12 ? h + 12 : h;
    case "점심":
    case "낮":
      return h < 7 ? h + 12 : h;
    case "오전":
    case "아침":
    case "새벽":
      return h === 12 ? 0 : h;
    default:
      // "3시 회의"처럼 오전/오후를 생략하면 1~7시는 오후로 본다.
      return !colon && h >= 1 && h <= 7 ? h + 12 : h;
  }
}

function nextWeekdayFrom(today: string, wd: number): string {
  return addDays(today, (wd - weekday(today) + 7) % 7);
}

export function parseQuickAdd(input: string, today: string, categories: Category[]): ParsedQuickAdd {
  let text = ` ${input} `;
  // 매칭된 부분을 잘라내고 fn을 호출한다. fn이 문자열을 돌려주면 그 문자열로 대신 바꾼다.
  const cut = (re: RegExp, fn: (...m: string[]) => unknown) => {
    text = text.replace(re, (...args) => {
      const r = fn(...(args.slice(0, -2) as string[]));
      return typeof r === "string" ? r : " ";
    });
  };

  const result: ParsedQuickAdd = {
    title: "",
    priority: 4,
    tags: [],
    repeat: { freq: "none", interval: 1 },
    kind: "task",
  };

  // #태그
  cut(/\s#([^\s#]+)/g, (_, tag) => {
    if (!result.tags.includes(tag)) result.tags.push(tag);
  });

  // @카테고리
  cut(/\s@([^\s@]+)/g, (whole, name) => {
    const found = categories.find((c) => c.name.toLowerCase().startsWith(name.toLowerCase()));
    if (!found) return whole; // 없는 카테고리는 제목에 남긴다
    result.categoryId = found.id;
  });

  // 우선순위: !1 !2 !3 또는 !!! !! !
  cut(/\s!([1-3])(?=\s)/, (_, p) => (result.priority = Number(p) as Priority));
  cut(/\s(!{1,3})(?=\s)/, (_, marks) => (result.priority = (4 - marks.length) as Priority));

  // 반복
  cut(new RegExp(`\\s매일${END}`), () => (result.repeat = { freq: "daily", interval: 1 }));
  cut(new RegExp(`\\s(?:매\\s*평일|평일마다|평일\\s*매일)${END}`), () => (result.repeat = { freq: "weekdays", interval: 1 }));
  cut(new RegExp(`\\s(?:매주|주마다)(?:\\s*([${WD}])요일)?${PARTICLE}${END}`), (_, d) => {
    result.repeat = { freq: "weekly", interval: 1 };
    if (d) result.date = nextWeekdayFrom(today, WD.indexOf(d));
  });
  cut(new RegExp(`\\s(?:격주)(?:\\s*([${WD}])요일)?${PARTICLE}${END}`), (_, d) => {
    result.repeat = { freq: "weekly", interval: 2 };
    if (d) result.date = nextWeekdayFrom(today, WD.indexOf(d));
  });
  cut(new RegExp(`\\s(?:매달|매월)(?:\\s*(\\d{1,2})일)?${PARTICLE}${END}`), (_, d) => {
    result.repeat = { freq: "monthly", interval: 1 };
    if (d) result.date = dayOfMonthFrom(today, Number(d));
  });
  cut(new RegExp(`\\s(?:매년|매해)${END}`), () => (result.repeat = { freq: "yearly", interval: 1 }));

  // 날짜
  const setDate = (key: string) => {
    if (!result.date) result.date = key;
  };
  cut(new RegExp(`\\s(\\d{4})[-./](\\d{1,2})[-./](\\d{1,2})${PARTICLE}${END}`), (_, y, m, d) =>
    setDate(toKey(new Date(Number(y), Number(m) - 1, Number(d)))),
  );
  cut(new RegExp(`\\s(\\d{1,2})\\s*월\\s*(\\d{1,2})\\s*일${PARTICLE}${END}`), (_, m, d) =>
    setDate(monthDayFrom(today, Number(m), Number(d))),
  );
  cut(new RegExp(`\\s(\\d{1,2})/(\\d{1,2})${PARTICLE}${END}`), (_, m, d) =>
    setDate(monthDayFrom(today, Number(m), Number(d))),
  );
  cut(new RegExp(`\\s(오늘|금일)${PARTICLE}${END}`), () => setDate(today));
  cut(new RegExp(`\\s(내일|낼)${PARTICLE}${END}`), () => setDate(addDays(today, 1)));
  cut(new RegExp(`\\s(모레)${PARTICLE}${END}`), () => setDate(addDays(today, 2)));
  cut(new RegExp(`\\s(글피)${PARTICLE}${END}`), () => setDate(addDays(today, 3)));
  cut(new RegExp(`\\s(\\d+)\\s*(일|주|주일|개월|달)\\s*(?:후|뒤)${PARTICLE}${END}`), (_, n, unit) => {
    const count = Number(n);
    if (unit === "일") setDate(addDays(today, count));
    else if (unit.startsWith("주")) setDate(addDays(today, count * 7));
    else setDate(addMonths(today, count));
  });
  cut(new RegExp(`\\s(다다음\\s*주|다음\\s*주|담주|이번\\s*주|금주)\\s*([${WD}])(?:요일)?${PARTICLE}${END}`), (_, w, d) => {
    const offset = w.startsWith("다다음") ? 14 : w.startsWith("다음") || w === "담주" ? 7 : 0;
    const monday = startOfWeek(today, 1);
    setDate(addDays(monday, offset + ((WD.indexOf(d) + 6) % 7)));
  });
  cut(new RegExp(`\\s(이번\\s*)?주말${PARTICLE}${END}`), () => setDate(nextWeekdayFrom(today, 6)));
  cut(new RegExp(`\\s([${WD}])요일${PARTICLE}${END}`), (_, d) => setDate(nextWeekdayFrom(today, WD.indexOf(d))));
  cut(new RegExp(`\\s(\\d{1,2})일${PARTICLE}${END}`), (_, d) => setDate(dayOfMonthFrom(today, Number(d))));

  // 시간 (범위 포함)
  const range = new RegExp(`\\s${TIME}(?:\\s*(?:~|-|–|부터)\\s*${TIME}\\s*(?:까지)?)?${PARTICLE}${END}`);
  cut(range, (_, m1, h1, c1, mi1, half1, m2, h2, c2, mi2, half2) => {
    const sh = toHour(Number(h1), m1, c1 !== undefined);
    const sm = Number(c1 ?? mi1 ?? (half1 ? 30 : 0));
    const startMin = sh * 60 + sm;
    result.start = minToTime(startMin);
    if (h2) {
      let eh = toHour(Number(h2), m2 ?? m1, c2 !== undefined);
      if (eh * 60 < startMin && eh < 12) eh += 12;
      result.end = minToTime(eh * 60 + Number(c2 ?? mi2 ?? (half2 ? 30 : 0)));
    }
  });
  if (result.start && !result.end) {
    cut(/\s(\d+)\s*시간(?:\s*(\d+)\s*분)?\s*(?:동안)?(?=\s)/, (_, h, m) => {
      result.end = minToTime(timeToMin(result.start!) + Number(h) * 60 + Number(m ?? 0));
    });
    cut(/\s(\d+)\s*분\s*(?:동안)?(?=\s)/, (_, m) => {
      result.end = minToTime(timeToMin(result.start!) + Number(m));
    });
  }

  if (result.start) {
    result.kind = "event";
    if (!result.date) result.date = today;
    if (!result.end) result.end = minToTime(timeToMin(result.start) + 60);
  }
  if (result.repeat.freq !== "none" && !result.date) result.date = today;

  result.title = text.replace(/\s+/g, " ").trim();
  return result;
}

/** 오늘 이후로 가장 가까운 "d일" */
function dayOfMonthFrom(today: string, d: number): string {
  const t = fromKey(today);
  for (let i = 0; i < 12; i++) {
    const y = t.getFullYear();
    const m = t.getMonth() + i;
    const date = new Date(y, m, 1);
    if (d <= daysInMonth(date.getFullYear(), date.getMonth())) {
      const key = toKey(new Date(date.getFullYear(), date.getMonth(), d));
      if (key >= today) return key;
    }
  }
  return today;
}

/** 오늘 이후로 가장 가까운 "m월 d일" (지났으면 내년) */
function monthDayFrom(today: string, m: number, d: number): string {
  const year = fromKey(today).getFullYear();
  const key = toKey(new Date(year, m - 1, d));
  return key >= today ? key : toKey(new Date(year + 1, m - 1, d));
}
