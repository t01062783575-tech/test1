"use client";

import { useRef, useState } from "react";
import { todayKey } from "@/lib/date";
import { download, toICS } from "@/lib/ics";
import { COLORS, normalize, uid, useStore } from "@/lib/store";
import type { Settings, ThemeSetting } from "@/lib/types";
import { Button, Icon, Modal } from "./ui";

const row = "flex items-center justify-between gap-4 py-2.5 text-sm";
const select = "rounded-lg border border-line bg-surface-2 px-2 py-1.5 text-sm";

export function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { data, dispatch } = useStore();
  const { settings } = data;
  const fileRef = useRef<HTMLInputElement>(null);
  const [newCat, setNewCat] = useState("");
  const [message, setMessage] = useState("");
  const update = (patch: Partial<Settings>) => dispatch({ type: "updateSettings", patch });

  const importFile = async (file: File) => {
    try {
      const parsed = normalize(JSON.parse(await file.text()));
      if (!confirm(`항목 ${parsed.items.length}개, 습관 ${parsed.habits.length}개를 불러와요. 지금 데이터는 덮어써져요. 계속할까요?`)) return;
      dispatch({ type: "replace", data: parsed });
      setMessage("백업을 불러왔어요.");
    } catch {
      setMessage("파일을 읽지 못했어요. 이 앱에서 내보낸 JSON 파일인지 확인해주세요.");
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="설정">
      <div className="divide-y divide-line px-5">
        <section className="py-3">
          <h3 className="mb-1 text-xs font-semibold text-muted">화면</h3>
          <div className={row}>
            <span>테마</span>
            <select value={settings.theme} onChange={(e) => update({ theme: e.target.value as ThemeSetting })} className={select}>
              <option value="system">시스템 설정 따르기</option>
              <option value="light">라이트</option>
              <option value="dark">다크</option>
            </select>
          </div>
          <div className={row}>
            <span>한 주의 시작</span>
            <select value={settings.weekStart} onChange={(e) => update({ weekStart: Number(e.target.value) as 0 | 1 })} className={select}>
              <option value={0}>일요일</option>
              <option value={1}>월요일</option>
            </select>
          </div>
          <label className={row}>
            <span>공휴일 표시 (대한민국)</span>
            <input type="checkbox" checked={settings.showHolidays} onChange={(e) => update({ showHolidays: e.target.checked })} className="h-4 w-4 accent-[var(--accent)]" />
          </label>
        </section>

        <section className="py-3">
          <h3 className="mb-1 text-xs font-semibold text-muted">알림 · 집중 타이머</h3>
          <label className={row}>
            <span>
              브라우저 알림
              <span className="block text-xs text-muted">이 탭이 열려 있을 때 일정 알림을 보내요</span>
            </span>
            <input
              type="checkbox"
              checked={settings.notifications}
              onChange={async (e) => {
                const on = e.target.checked;
                if (on && "Notification" in window && Notification.permission !== "granted") {
                  const p = await Notification.requestPermission();
                  if (p !== "granted") {
                    setMessage("브라우저에서 알림 권한을 허용해야 해요.");
                    return;
                  }
                }
                update({ notifications: on });
              }}
              className="h-4 w-4 accent-[var(--accent)]"
            />
          </label>
          <div className={row}>
            <span>집중 시간</span>
            <select value={settings.focusMinutes} onChange={(e) => update({ focusMinutes: Number(e.target.value) })} className={select}>
              {[15, 20, 25, 30, 45, 50, 60, 90].map((m) => (
                <option key={m} value={m}>
                  {m}분
                </option>
              ))}
            </select>
          </div>
          <div className={row}>
            <span>휴식 시간</span>
            <select value={settings.breakMinutes} onChange={(e) => update({ breakMinutes: Number(e.target.value) })} className={select}>
              {[3, 5, 10, 15, 20].map((m) => (
                <option key={m} value={m}>
                  {m}분
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className="py-3">
          <h3 className="mb-2 text-xs font-semibold text-muted">카테고리</h3>
          <div className="space-y-1.5">
            {data.categories.map((c) => (
              <div key={c.id} className="flex items-center gap-2">
                <button
                  onClick={() =>
                    dispatch({
                      type: "upsertCategory",
                      category: { ...c, color: COLORS[(COLORS.indexOf(c.color) + 1) % COLORS.length] },
                    })
                  }
                  className="h-5 w-5 shrink-0 rounded-full"
                  style={{ background: c.color }}
                  title="눌러서 색상 바꾸기"
                  aria-label="색상 바꾸기"
                />
                <input
                  value={c.name}
                  onChange={(e) => dispatch({ type: "upsertCategory", category: { ...c, name: e.target.value } })}
                  className="flex-1 rounded-md bg-transparent px-2 py-1 text-sm outline-none hover:bg-surface-2 focus:bg-surface-2"
                />
                <button
                  onClick={() => {
                    if (confirm(`'${c.name}' 카테고리를 삭제할까요? 항목은 지워지지 않아요.`)) dispatch({ type: "deleteCategory", id: c.id });
                  }}
                  className="p-1 text-muted hover:text-danger"
                  aria-label="카테고리 삭제"
                >
                  <Icon name="trash" size={15} />
                </button>
              </div>
            ))}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!newCat.trim()) return;
                dispatch({
                  type: "upsertCategory",
                  category: { id: uid(), name: newCat.trim(), color: COLORS[data.categories.length % COLORS.length] },
                });
                setNewCat("");
              }}
              className="flex items-center gap-2"
            >
              <Icon name="plus" size={16} className="ml-1 text-muted" />
              <input
                value={newCat}
                onChange={(e) => setNewCat(e.target.value)}
                placeholder="새 카테고리 이름 후 Enter"
                className="flex-1 bg-transparent px-2 py-1 text-sm outline-none placeholder:text-muted"
              />
            </form>
          </div>
        </section>

        <section className="py-3">
          <h3 className="mb-1 text-xs font-semibold text-muted">데이터</h3>
          <p className="mb-3 text-xs text-muted">
            모든 데이터는 이 브라우저에만 저장돼요. 다른 기기로 옮기거나 잃어버리지 않도록 가끔 백업하세요.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => download(`planner-backup-${todayKey()}.json`, JSON.stringify(data, null, 2), "application/json")}>
              <Icon name="download" size={16} /> 백업 내보내기
            </Button>
            <Button variant="outline" onClick={() => fileRef.current?.click()}>
              <Icon name="upload" size={16} /> 백업 불러오기
            </Button>
            <Button variant="outline" onClick={() => download(`planner-${todayKey()}.ics`, toICS(data.items), "text/calendar")}>
              <Icon name="calendar" size={16} /> 캘린더(.ics) 내보내기
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void importFile(f);
                e.target.value = "";
              }}
            />
          </div>
          {message && <p className="mt-2 text-xs text-accent">{message}</p>}
          <div className="mt-4">
            <Button
              variant="danger"
              onClick={() => {
                if (confirm("모든 할일·일정·습관 기록을 지울까요? 되돌릴 수 없어요.")) {
                  dispatch({ type: "replace", data: normalize({ categories: data.categories, settings }) });
                  setMessage("모든 기록을 지웠어요.");
                }
              }}
            >
              모든 데이터 지우기
            </Button>
          </div>
        </section>

        <section className="py-3 text-xs text-muted">
          <h3 className="mb-2 font-semibold">단축키</h3>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {[
              ["Ctrl/⌘ + K", "검색 · 명령"],
              ["N", "새 항목"],
              ["Q", "빠른 추가 입력"],
              ["F", "집중 타이머"],
              ["1 ~ 6", "화면 전환"],
              ["← / →", "캘린더 이전/다음"],
              ["T", "캘린더 오늘로"],
              ["M / W / D", "월 · 주 · 일 보기"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2">
                <kbd className="font-mono">{k}</kbd>
                <span>{v}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </Modal>
  );
}
