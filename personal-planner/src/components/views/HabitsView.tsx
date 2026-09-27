"use client";

import { useState } from "react";
import { WEEKDAYS, addDays, fromKey, rangeKeys, weekday } from "@/lib/date";
import { COLORS, uid, useStore } from "@/lib/store";
import type { Habit } from "@/lib/types";
import { useApp } from "../AppContext";
import { Button, Icon } from "../ui";

/** 오늘(또는 오늘 아직 안 했으면 어제)부터 거꾸로 이어진 연속 일수 */
function streak(h: Habit, today: string): number {
  const set = new Set(h.log);
  let d = set.has(today) ? today : addDays(today, -1);
  let n = 0;
  while (set.has(d)) {
    n++;
    d = addDays(d, -1);
  }
  return n;
}

function bestStreak(h: Habit): number {
  const sorted = [...h.log].sort();
  let best = 0;
  let run = 0;
  let prev = "";
  for (const d of sorted) {
    run = prev && addDays(prev, 1) === d ? run + 1 : 1;
    best = Math.max(best, run);
    prev = d;
  }
  return best;
}

export function HabitsView() {
  const { data, dispatch } = useStore();
  const { today } = useApp();
  const [name, setName] = useState("");
  const [color, setColor] = useState(COLORS[2]);
  const week = rangeKeys(addDays(today, -6), 7);
  // 최근 16주 잔디 (요일 정렬)
  const heatStart = addDays(today, -(7 * 15 + weekday(today)));
  const heatDays = rangeKeys(heatStart, 7 * 15 + weekday(today) + 1);

  const add = () => {
    if (!name.trim()) return;
    dispatch({ type: "upsertHabit", habit: { id: uid(), name: name.trim(), color, log: [], createdAt: new Date().toISOString() } });
    setName("");
  };

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
      <div>
        <h1 className="text-2xl font-bold">습관 트래커</h1>
        <p className="mt-1 text-sm text-muted">매일 반복하고 싶은 습관을 체크하고 연속 기록을 쌓아보세요.</p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          add();
        }}
        className="flex flex-wrap items-center gap-2 rounded-2xl border border-line bg-surface p-3"
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="새 습관 (예: 물 2L 마시기, 30분 독서)"
          className="h-9 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
        />
        <div className="flex gap-1">
          {COLORS.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setColor(c)}
              className={`h-5 w-5 rounded-full ${color === c ? "ring-2 ring-ink ring-offset-2 ring-offset-surface" : ""}`}
              style={{ background: c }}
              aria-label={`색상 ${c}`}
            />
          ))}
        </div>
        <Button variant="primary" type="submit">
          <Icon name="plus" size={16} /> 추가
        </Button>
      </form>

      {data.habits.length === 0 && (
        <p className="rounded-2xl border border-dashed border-line p-8 text-center text-sm text-muted">아직 습관이 없어요.</p>
      )}

      {data.habits.length > 0 && (
        <div className="scroll-thin overflow-x-auto rounded-2xl border border-line bg-surface">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="text-xs text-muted">
                <th className="px-4 py-3 text-left font-medium">습관</th>
                {week.map((d) => (
                  <th key={d} className={`w-10 py-3 font-medium ${d === today ? "text-accent" : ""}`}>
                    <div>{WEEKDAYS[weekday(d)]}</div>
                    <div>{fromKey(d).getDate()}</div>
                  </th>
                ))}
                <th className="px-3 py-3 font-medium">연속</th>
                <th className="px-3 py-3 font-medium">최고</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {data.habits.map((h) => (
                <tr key={h.id} className="group border-t border-line">
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: h.color }} />
                      {h.name}
                    </div>
                  </td>
                  {week.map((d) => {
                    const on = h.log.includes(d);
                    return (
                      <td key={d} className="text-center">
                        <button
                          onClick={() => dispatch({ type: "toggleHabit", id: h.id, date: d })}
                          className="mx-auto flex h-7 w-7 items-center justify-center rounded-lg border transition"
                          style={on ? { background: h.color, borderColor: h.color, color: "#fff" } : { borderColor: "var(--line)" }}
                          aria-label={`${d} ${on ? "체크 해제" : "체크"}`}
                        >
                          {on && "✓"}
                        </button>
                      </td>
                    );
                  })}
                  <td className="px-3 text-center font-semibold">🔥 {streak(h, today)}</td>
                  <td className="px-3 text-center text-muted">{bestStreak(h)}</td>
                  <td>
                    <button
                      onClick={() => {
                        if (confirm(`'${h.name}' 습관을 삭제할까요? 기록도 함께 지워져요.`)) dispatch({ type: "deleteHabit", id: h.id });
                      }}
                      className="p-1 text-muted opacity-0 group-hover:opacity-100 hover:text-danger max-sm:opacity-60"
                      aria-label="습관 삭제"
                    >
                      <Icon name="trash" size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.habits.map((h) => {
        const set = new Set(h.log);
        const last30 = rangeKeys(addDays(today, -29), 30).filter((d) => set.has(d)).length;
        return (
          <div key={h.id} className="rounded-2xl border border-line bg-surface p-4">
            <div className="mb-3 flex items-center justify-between text-sm">
              <span className="font-semibold">{h.name}</span>
              <span className="text-xs text-muted">최근 30일 {Math.round((last30 / 30) * 100)}% 달성</span>
            </div>
            <div className="scroll-thin overflow-x-auto">
              <div className="grid w-max grid-flow-col grid-rows-7 gap-[3px]">
                {heatDays.map((d) => (
                  <div
                    key={d}
                    title={`${d}${set.has(d) ? " ✓" : ""}`}
                    className="h-3.5 w-3.5 rounded-[3px]"
                    style={{ background: set.has(d) ? h.color : "var(--surface-2)" }}
                  />
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
