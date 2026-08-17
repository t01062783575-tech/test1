import EmailSignupForm from "@/components/EmailSignupForm";

const painPoints = [
  "쿠팡, 스마트스토어, 각 채널에 매일 들어가서 주문을 하나씩 확인하시나요?",
  "확인한 주문을 다시 엑셀에 옮겨 적으시나요?",
  "재고가 떨어지고 나서야 부랴부랴 발주를 넣으시나요?",
  "밀려있는 리뷰에 밤늦게 하나하나 답글을 다시나요?",
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
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
        <path d="M10 6.5h4M6.5 10v4M17.5 10v4M10 17.5h4" strokeLinecap="round" />
      </svg>
    ),
    title: "멀티채널 주문 통합",
    description:
      "쿠팡·스마트스토어 주문을 한 화면에서 실시간으로 모아보고, 신규 주문부터 배송 상태까지 한눈에 관리하세요.",
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
          d="M12 2v6M12 2 8 6M12 2l4 4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <rect x="4" y="9" width="16" height="12" rx="2" />
        <path d="M8 14h8M8 17h5" strokeLinecap="round" />
      </svg>
    ),
    title: "재고 자동 알림 + 발주",
    description:
      "재고가 기준치 아래로 떨어지면 즉시 알림을 받고, 발주서까지 자동으로 만들어져요. 품절로 놓치는 매출이 사라집니다.",
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
          d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    title: "리뷰 자동 응대",
    description:
      "리뷰 내용을 분석해 상황에 맞는 답글 초안을 자동으로 작성해요. 확인 후 클릭 한 번이면 등록까지 끝.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col bg-white text-slate-900">
      {/* Header */}
      <header className="w-full border-b border-slate-100">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5">
          <span className="text-lg font-bold tracking-tight">
            셀러오토
            <span className="text-blue-600">.</span>
          </span>
          <span className="hidden text-sm text-slate-500 sm:block">
            스마트스토어 · 쿠팡 셀러를 위한 자동화
          </span>
        </div>
      </header>

      {/* Hero */}
      <section className="w-full bg-gradient-to-b from-slate-50 to-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center px-6 py-20 text-center sm:py-28">
          <span className="mb-6 inline-flex items-center rounded-full border border-blue-100 bg-blue-50 px-4 py-1.5 text-sm font-medium text-blue-700">
            사전예약 오픈 · 얼리버드 혜택 제공
          </span>
          <h1 className="max-w-3xl text-3xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl sm:leading-tight">
            자피어 대신 — 스마트스토어 사장님만을 위한
            <br className="hidden sm:block" /> 자동화, 세팅 10분
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-relaxed text-slate-600 sm:text-lg">
            쿠팡·스마트스토어 주문을 한곳에 모으고,
            <br className="hidden sm:block" />
            재고 부족·리뷰 응대까지 자동으로
          </p>

          <div className="mt-10 flex w-full flex-col items-center">
            <EmailSignupForm id="hero-email" variant="light" />
          </div>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-500">
            <span>✓ 신용카드 필요 없음</span>
            <span>✓ 세팅 10분 완료</span>
            <span>✓ 국내 셀러 전용 설계</span>
          </div>
        </div>
      </section>

      {/* Problem empathy */}
      <section className="w-full bg-slate-900 py-20 text-white sm:py-24">
        <div className="mx-auto w-full max-w-4xl px-6 text-center">
          <h2 className="text-2xl font-bold leading-snug sm:text-3xl">
            매일 각 채널 들어가서 주문 확인하고, 엑셀에 옮기고,
            <br className="hidden sm:block" />
            재고 떨어지면 그제서야 발주하시나요?
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
          <p className="mt-10 text-lg font-semibold text-blue-300">
            이 모든 걸 자동화가 대신합니다.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="w-full bg-white py-20 sm:py-24">
        <div className="mx-auto w-full max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-2xl font-bold text-slate-900 sm:text-3xl">
              사장님 대신 반복 업무를 처리해요
            </h2>
            <p className="mt-3 text-slate-600">
              복잡한 설정 없이, 딱 필요한 자동화만 10분 만에 시작하세요.
            </p>
          </div>

          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl border border-slate-200 p-7 transition hover:border-blue-200 hover:shadow-md"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
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
      <section className="w-full bg-blue-700 py-20 sm:py-24">
        <div className="mx-auto flex w-full max-w-3xl flex-col items-center px-6 text-center">
          <h2 className="text-2xl font-bold leading-snug text-white sm:text-3xl">
            지금 사전예약하고
            <br className="hidden sm:block" />
            가장 먼저 자동화를 경험하세요
          </h2>
          <p className="mt-4 text-blue-100">
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
          <span>© 2026 셀러오토. All rights reserved.</span>
          <span>스마트스토어·쿠팡 셀러를 위한 업무 자동화 SaaS</span>
        </div>
      </footer>
    </div>
  );
}
