import { describe, expect, it } from "vitest";
import { mockGenerate } from "@/lib/mockAi";

describe("mockGenerate", () => {
  it("returns a non-empty string for a normal input", () => {
    const result = mockGenerate("마케팅 문구 작성해줘");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("includes the trimmed input text in the generated output", () => {
    const result = mockGenerate("  안녕하세요  ");
    expect(result).toContain("안녕하세요");
  });
});
