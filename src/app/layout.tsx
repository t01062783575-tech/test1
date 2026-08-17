import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "자동화, 세팅 10분 — 스마트스토어·쿠팡 셀러를 위한 업무 자동화",
  description:
    "쿠팡·스마트스토어 주문을 한곳에 모으고, 재고 부족·리뷰 응대까지 자동으로. 자피어 대신 셀러만을 위한 자동화 SaaS, 사전예약하고 가장 먼저 만나보세요.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
