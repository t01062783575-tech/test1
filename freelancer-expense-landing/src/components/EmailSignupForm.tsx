"use client";

import { useActionState } from "react";
import { joinWaitlist, type WaitlistState } from "@/app/actions";

const initialState: WaitlistState = { status: "idle", message: "" };

export default function EmailSignupForm({
  id,
  variant = "light",
}: {
  id: string;
  variant?: "light" | "dark";
}) {
  const [state, formAction, isPending] = useActionState(
    joinWaitlist,
    initialState
  );

  const isDark = variant === "dark";

  return (
    <div className="w-full max-w-md">
      <form
        action={formAction}
        className="flex flex-col gap-3 sm:flex-row sm:gap-2"
      >
        <label htmlFor={id} className="sr-only">
          이메일 주소
        </label>
        <input
          id={id}
          name="email"
          type="email"
          required
          placeholder="이메일 주소를 입력하세요"
          className={`w-full rounded-lg border px-4 py-3 text-base outline-none transition focus:ring-2 focus:ring-teal-500 ${
            isDark
              ? "border-white/20 bg-white/10 text-white placeholder:text-white/50"
              : "border-slate-300 bg-white text-slate-900 placeholder:text-slate-400"
          }`}
        />
        <button
          type="submit"
          disabled={isPending}
          className="shrink-0 rounded-lg bg-teal-600 px-6 py-3 text-base font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isPending ? "등록 중..." : "사전예약하기"}
        </button>
      </form>
      {state.message && (
        <p
          className={`mt-3 text-sm ${
            state.status === "error"
              ? "text-red-500"
              : isDark
              ? "text-emerald-300"
              : "text-emerald-600"
          }`}
          role="status"
        >
          {state.message}
        </p>
      )}
      <p
        className={`mt-3 text-xs ${
          isDark ? "text-white/50" : "text-slate-400"
        }`}
      >
        스팸 없이 출시 소식만 보내드려요. 언제든 구독을 취소할 수 있어요.
      </p>
    </div>
  );
}
