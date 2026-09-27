import { addDays, weekday } from "./date";

// 양력 공휴일 (매년 동일)
const SOLAR: Record<string, string> = {
  "01-01": "신정",
  "03-01": "삼일절",
  "05-05": "어린이날",
  "06-06": "현충일",
  "08-15": "광복절",
  "10-03": "개천절",
  "10-09": "한글날",
  "12-25": "성탄절",
};

// 토·일요일과 겹치면 대체공휴일이 생기는 양력 공휴일
const SOLAR_SUBSTITUTE = new Set(["03-01", "05-05", "08-15", "10-03", "10-09", "12-25"]);

// 음력 공휴일·선거일 등 해마다 달라지는 날 (대체공휴일 포함)
const YEARLY: Record<string, string> = {
  "2025-01-27": "임시공휴일",
  "2025-01-28": "설날 연휴",
  "2025-01-29": "설날",
  "2025-01-30": "설날 연휴",
  "2025-05-05": "부처님오신날",
  "2025-05-06": "대체공휴일",
  "2025-06-03": "대통령선거일",
  "2025-10-05": "추석 연휴",
  "2025-10-06": "추석",
  "2025-10-07": "추석 연휴",
  "2025-10-08": "대체공휴일",
  "2026-02-16": "설날 연휴",
  "2026-02-17": "설날",
  "2026-02-18": "설날 연휴",
  "2026-05-24": "부처님오신날",
  "2026-05-25": "대체공휴일",
  "2026-06-03": "지방선거일",
  "2026-09-24": "추석 연휴",
  "2026-09-25": "추석",
  "2026-09-26": "추석 연휴",
  "2027-02-06": "설날 연휴",
  "2027-02-07": "설날",
  "2027-02-08": "설날 연휴",
  "2027-02-09": "대체공휴일",
  "2027-05-13": "부처님오신날",
  "2027-09-14": "추석 연휴",
  "2027-09-15": "추석",
  "2027-09-16": "추석 연휴",
};

const cache = new Map<number, Map<string, string>>();

function build(year: number): Map<string, string> {
  const map = new Map<string, string>();
  for (const [key, name] of Object.entries(YEARLY)) {
    if (key.startsWith(`${year}-`)) map.set(key, name);
  }
  for (const [md, name] of Object.entries(SOLAR)) {
    const key = `${year}-${md}`;
    map.set(key, map.has(key) ? `${map.get(key)}·${name}` : name);
  }
  for (const md of SOLAR_SUBSTITUTE) {
    const key = `${year}-${md}`;
    const wd = weekday(key);
    if (wd !== 0 && wd !== 6) continue;
    let sub = addDays(key, wd === 6 ? 2 : 1);
    while (map.has(sub) || weekday(sub) === 0 || weekday(sub) === 6) {
      sub = addDays(sub, 1);
    }
    map.set(sub, "대체공휴일");
  }
  return map;
}

export function holidayName(key: string): string | undefined {
  const year = Number(key.slice(0, 4));
  let map = cache.get(year);
  if (!map) {
    map = build(year);
    cache.set(year, map);
  }
  return map.get(key);
}
