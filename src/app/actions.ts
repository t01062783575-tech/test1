"use server";

import { getSupabaseServerClient } from "@/lib/supabase";

export type WaitlistState = {
  status: "idle" | "success" | "error";
  message: string;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function joinWaitlist(
  _prevState: WaitlistState,
  formData: FormData
): Promise<WaitlistState> {
  const email = String(formData.get("email") ?? "").trim();

  if (!email || !EMAIL_REGEX.test(email)) {
    return { status: "error", message: "올바른 이메일 주소를 입력해주세요." };
  }

  try {
    const supabase = getSupabaseServerClient();
    const { error } = await supabase
      .from("waitlist_signups")
      .insert({ email });

    if (error) {
      if (error.code === "23505") {
        return {
          status: "success",
          message: "이미 등록된 이메일이에요. 곧 소식 전해드릴게요!",
        };
      }
      throw error;
    }

    return {
      status: "success",
      message: "사전예약이 완료됐어요. 출시 소식을 가장 먼저 알려드릴게요!",
    };
  } catch (err) {
    console.error("waitlist signup failed", err);
    return {
      status: "error",
      message: "일시적인 오류가 발생했어요. 잠시 후 다시 시도해주세요.",
    };
  }
}
