"use client";

import dynamic from "next/dynamic";

// 모든 데이터가 브라우저(localStorage)에 있으므로 플래너는 클라이언트에서만 렌더링한다.
const Planner = dynamic(() => import("./Planner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-sm text-muted">불러오는 중…</div>
  ),
});

export default function PlannerLoader() {
  return <Planner />;
}
