"use client";

import { useRouter } from "next/navigation";

export default function LogoutButton() {
  const router = useRouter();

  function handleLogout() {
    localStorage.removeItem("workspace_user");
    router.push("/login");
  }

  return (
    <button
      onClick={handleLogout}
      className="shrink-0 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
    >
      로그아웃
    </button>
  );
}
