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
  title: "흩어진 경비, 한 번에 정리 — 프리랜서·1인사업자 경비 자동정리",
  description:
    "개인카드, 사업카드, 계좌이체, 현금영수증, 카카오페이까지 자동으로 모아 매달 장부를 완성해요. 종소세 신고 시즌에도 영수증 찾느라 밤새우지 마세요. 지금 사전예약하세요.",
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
