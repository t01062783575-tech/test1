import LoginForm from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-bold text-slate-900">로그인</h1>
        <p className="mt-1 text-sm text-slate-500">
          AI 콘텐츠 워크스페이스에 오신 것을 환영합니다.
        </p>
        <LoginForm />
      </div>
    </main>
  );
}
