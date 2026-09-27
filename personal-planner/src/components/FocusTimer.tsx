"use client";

import { useEffect, useState } from "react";
import { uid, useStore } from "@/lib/store";
import { useApp } from "./AppContext";
import { Icon } from "./ui";

type Phase = "focus" | "break";

export function notify(title: string, body: string) {
  try {
    if ("Notification" in window && Notification.permission === "granted") new Notification(title, { body, icon: "/icon.svg" });
  } catch {
    // 알림을 지원하지 않는 환경
  }
}

/** 뽀모도로 집중 타이머 (화면 오른쪽 아래에 떠 있는 패널) */
export function FocusTimer({ itemId, onItemChange, onClose }: { itemId?: string; onItemChange: (id?: string) => void; onClose: () => void }) {
  const { data, dispatch } = useStore();
  const { today } = useApp();
  const { focusMinutes, breakMinutes } = data.settings;
  const [phase, setPhase] = useState<Phase>("focus");
  // 실행 중이면 endAt, 멈춰 있으면 remaining(초)을 쓴다
  const [endAt, setEndAt] = useState<number | null>(null);
  const [remaining, setRemaining] = useState(focusMinutes * 60);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [minimized, setMinimized] = useState(false);

  const item = itemId ? data.items.find((i) => i.id === itemId) : undefined;
  const openTasks = data.items.filter((i) => i.kind === "task" && !i.done && (i.repeat.freq === "none" || i.date));
  const left = endAt ? Math.max(0, Math.round((endAt - nowMs) / 1000)) : remaining;

  useEffect(() => {
    if (!endAt) return;
    const id = setInterval(() => {
      const t = Date.now();
      setNowMs(t);
      if (t < endAt) return;
      // 한 구간이 끝남
      if (phase === "focus") {
        dispatch({ type: "addFocus", session: { id: uid(), date: today, minutes: focusMinutes, itemId } });
        notify("집중 완료! 🎉", `${focusMinutes}분 집중했어요. ${breakMinutes}분 쉬어가세요.`);
        setPhase("break");
        setEndAt(t + breakMinutes * 60 * 1000);
      } else {
        notify("휴식 끝", "다시 집중해볼까요?");
        setPhase("focus");
        setEndAt(null);
        setRemaining(focusMinutes * 60);
      }
    }, 500);
    return () => clearInterval(id);
  }, [endAt, phase, focusMinutes, breakMinutes, itemId, today, dispatch]);

  const toggleRun = () => {
    if (endAt) {
      setRemaining(left);
      setEndAt(null);
    } else {
      if ("Notification" in window && Notification.permission === "default") void Notification.requestPermission();
      const t = Date.now();
      setNowMs(t);
      setEndAt(t + left * 1000);
    }
  };

  const reset = () => {
    // 집중 중간에 멈추면 1분 이상 한 만큼 기록
    if (phase === "focus") {
      const spent = Math.floor((focusMinutes * 60 - left) / 60);
      if (spent >= 1) dispatch({ type: "addFocus", session: { id: uid(), date: today, minutes: spent, itemId } });
    }
    setEndAt(null);
    setPhase("focus");
    setRemaining(focusMinutes * 60);
  };

  const total = (phase === "focus" ? focusMinutes : breakMinutes) * 60;
  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  const color = phase === "focus" ? "var(--accent)" : "#10b981";
  const r = 52;
  const c = 2 * Math.PI * r;

  if (minimized) {
    return (
      <button
        onClick={() => setMinimized(false)}
        className="fixed right-4 bottom-20 z-40 flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 font-mono text-sm font-semibold shadow-lg md:bottom-4"
        style={{ color }}
      >
        <Icon name="timer" size={16} /> {mm}:{ss}
      </button>
    );
  }

  return (
    <div className="fixed right-4 bottom-20 z-40 w-72 rounded-2xl border border-line bg-surface p-4 shadow-2xl md:bottom-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-semibold" style={{ color }}>
          {phase === "focus" ? "집중" : "휴식"}
        </span>
        <div className="flex gap-1">
          <button onClick={() => setMinimized(true)} className="rounded p-1 text-muted hover:bg-surface-2" aria-label="최소화">
            <span className="block h-0.5 w-3.5 bg-current" />
          </button>
          <button
            onClick={() => {
              reset();
              onClose();
            }}
            className="rounded p-1 text-muted hover:bg-surface-2"
            aria-label="닫기"
          >
            <Icon name="x" size={16} />
          </button>
        </div>
      </div>
      <div className="relative mx-auto h-32 w-32">
        <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
          <circle cx="60" cy="60" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="8" />
          <circle
            cx="60"
            cy="60"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (left / total)}
            className="transition-[stroke-dashoffset] duration-500"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-mono text-3xl font-semibold tabular-nums">
          {mm}:{ss}
        </div>
      </div>
      <select
        value={itemId ?? ""}
        onChange={(e) => onItemChange(e.target.value || undefined)}
        className="mt-3 w-full truncate rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-xs"
      >
        <option value="">할일 선택 안 함</option>
        {item && !openTasks.includes(item) && <option value={item.id}>{item.title}</option>}
        {openTasks.map((t) => (
          <option key={t.id} value={t.id}>
            {t.title}
          </option>
        ))}
      </select>
      <div className="mt-3 flex justify-center gap-2">
        <button onClick={toggleRun} className="flex items-center gap-1.5 rounded-full px-5 py-2 text-sm font-semibold text-white" style={{ background: color }}>
          <Icon name={endAt ? "pause" : "play"} size={14} /> {endAt ? "일시정지" : "시작"}
        </button>
        <button onClick={reset} className="rounded-full border border-line px-3 py-2 text-sm hover:bg-surface-2" title="처음으로">
          <Icon name="stop" size={14} />
        </button>
        {item && item.repeat.freq === "none" && (
          <button
            onClick={() => {
              dispatch({ type: "toggleDone", id: item.id });
              onItemChange(undefined);
            }}
            className="rounded-full border border-line px-3 py-2 text-xs hover:bg-surface-2"
            title="선택한 할일 완료"
          >
            완료
          </button>
        )}
      </div>
      <p className="mt-3 text-center text-[11px] text-muted">
        오늘 집중 {data.focus.filter((f) => f.date === today).reduce((s, f) => s + f.minutes, 0)}분
      </p>
    </div>
  );
}
