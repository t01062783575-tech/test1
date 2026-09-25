import { NextResponse } from "next/server";
import { mockGenerate } from "@/lib/mockAi";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const text = typeof body?.text === "string" ? body.text : "";

  await new Promise((resolve) => setTimeout(resolve, 500 + Math.random() * 500));

  const roll = Math.random();

  if (roll < 0.12) {
    return NextResponse.json(
      { error: "AI 제공자 응답이 지연되고 있어요." },
      { status: 500 }
    );
  }

  if (roll < 0.2) {
    const provider = undefined as unknown as { model: string };
    return NextResponse.json({ result: provider.model });
  }

  return NextResponse.json({
    id: crypto.randomUUID(),
    result: mockGenerate(text),
    createdAt: new Date().toISOString(),
  });
}
