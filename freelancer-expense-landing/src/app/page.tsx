import EmailSignupForm from "@/components/EmailSignupForm";

const painPoints = [
  "개인카드, 사업카드, 계좌이체, 현금영수증, 카카오페이... 채널마다 따로 확인하고 계신가요?",
  "신고 마감 직전에 몰아서 정리하다 놓친 경비, 없으셨나요?",
  "어떤 지출이 경비 처리가 되는지 매번 헷갈리진 않으셨나요?",
  "장부가 없어서 무기장 가산세를 걱정한 적, 있으셨나요?",
];

const features = [
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className="h-6 w-6"
        stroke="currentColor"
        strokeWidth={1.75}
      >
        <rect x="2.5" y="5" width="19" height="14" rx="2.5" />
        <path d="M2.5 9.5h19" strokeLinecap="round" />
        <path d="M6.5 14.5h4" strokeLinecap="round" />
      </svg>
    ),
    title: "카드·계좌·간편결제 자동 연동",
    description:
      "개인카드, 사업카드, 계좌이체, 현금영수증, 카카오페이까지 한 번만 연결하면 지출 내역이 자동으로 모여요.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className="h-6 w-6"
        stroke="currentColor"
        strokeWidth={1.75}
      >
        <path d="M5 3.5h11.5A2.5 2.5 0 0 1 19 6v14.5H7.5A2.5 2.5 0 0 1 5 18V3.5Z" />
        <path d="M5 18a2.5 2.5 0 0 1 2.5-2.5H19" strokeLinecap="round" />
        <path d="M9 8h6M9 11h6" strokeLinecap="round" />
      </svg>
    ),
    title: "무기장 가산세 걱정 없는 자동 장부",
    description:
      "모인 지출이 매달 자동으로 장부에 정리돼요. 종소세 신고철에도 미리 완성된 장부로 여유롭게 준비하세요.",
  },
  {
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className="h-6 w-6"
        stroke="currentColor"
        strokeWidth={1.75}
      >
        <path
          d="M12 3 4 6.5v5c0 4.6 3.2 8.4 8 9.5 4.8-1.1 8-4.9 8-9.5v-5L12 3Z"
          strokeLinejoin="round"
        />
        <path d="m9 12 2 2 4-4.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    title: "신고 성수기에도 끊김 없는 서버",
    description:
      "5월 종소세 성수기에 접속자가 몰려도 안정적으로 동작하도록 설계했어요. 마감 직전에도 걱정 없이 확인하세요.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col bg-white text-slate-900">
      {/* Header */}
      <header className="w-full border-b border-slate-100">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5">
          <span className="text-lg font-bold tracking-tight">
            경비모아
            <span className="text-teal-600">.</span>
          </span>
          <span className="hidden text-sm text-slate-500 sm:block">
            프리랜서 · 1인사업자를 위한 경비 자동정리
          </span>
        </div>
      </header>

      {/* Hero */}
      <section className="w-full bg-gradient-to-b from-teal-50 to-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center px-6 py-20 text-center sm:py-28">
          <span className="mb-6 inline-flex items-center rounded-full border border-teal-100 bg-teal-50 px-4 py-1.5 text-sm font-medium text-teal-700">
            사전예약 오픈 · 얼리버드 혜택 제공
          </span>
          <h1 className="max-w-3xl text-3xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl sm:leading-tight">
            카드도, 통장도, 카카오페이도
            <br className="hidden sm:block" /> — 흩어진 경비, 한 번에 정리
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-relaxed text-slate-600 sm:text-lg">
            5월 종소세 신고 때마다 영수증 찾느라 밤새우셨나요?
            <br className="hidden sm:block" />
            미리 자동으로 모아드립니다
          </p>

          <div className="mt-10 flex w-full flex-col items-center">
            <EmailSignupForm id="hero-email" variant="light" />
          </div>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-500">
            <span>✓ 신용카드 필요 없음</span>
            <span>✓ 연동 5분 완료</span>
            <span>✓ 프리랜서·1인사업자 전용 설계</span>
          </div>
        </div>
      </section>

      {/* Problem empathy */}
      <section className="w-full bg-slate-900 py-20 text-white sm:py-24">
        <div className="mx-auto w-full max-w-4xl px-6 text-center">
          <h2 className="text-2xl font-bold leading-snug sm:text-3xl">
            영수증은 흩어지고, 마감은 다가오고
          </h2>
          <ul className="mx-auto mt-10 grid max-w-2xl gap-4 text-left">
            {painPoints.map((point) => (
              <li
                key={point}
                className="flex items-start gap-3 rounded-xl bg-white/5 px-5 py-4 text-slate-200"
              >
                <span className="mt-0.5 text-red-400">✕</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
          <p className="mt-10 text-lg font-semibold text-teal-300">
            이 모든 걸 자동정리가 대신합니다.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="w-full bg-white py-20 sm:py-24">
        <div className="mx-auto w-full max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-2xl font-bold text-slate-900 sm:text-3xl">
              사장님 대신 경비 정리를 끝내드려요
            </h2>
            <p className="mt-3 text-slate-600">
              복잡한 설정 없이, 연동 한 번이면 매달 자동으로 장부가 완성돼요.
            </p>
          </div>

          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-200 p-7 transition hover:border-teal-200 hover:shadow-md"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50 text-teal-600">
                  {feature.icon}
                </div>
                <h3 className="mt-5 text-lg font-bold text-slate-900">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="w-full bg-teal-700 py-20 sm:py-24">
        <div className="mx-auto flex w-full max-w-3xl flex-col items-center px-6 text-center">
          <h2 className="text-2xl font-bold leading-snug text-white sm:text-3xl">
            지금 사전예약하고
            <br className="hidden sm:block" />
            가장 먼저 경비 자동정리를 경험하세요
          </h2>
          <p className="mt-4 text-teal-100">
            사전예약자 전원에게 출시 후 얼리버드 할인 혜택을 드려요.
          </p>
          <div className="mt-8 flex w-full flex-col items-center">
            <EmailSignupForm id="bottom-email" variant="dark" />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full border-t border-slate-100 bg-white py-8">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-2 px-6 text-center text-sm text-slate-400 sm:flex-row sm:justify-between sm:text-left">
          <span>© 2026 경비모아. All rights reserved.</span>
          <span>프리랜서·1인사업자를 위한 경비 자동정리 SaaS</span>
        </div>
      </footer>
    </div>
  );
}
