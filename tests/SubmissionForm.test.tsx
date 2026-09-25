import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import SubmissionForm from "@/components/SubmissionForm";

describe("SubmissionForm", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a validation message and does not call the API for empty input", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const onResult = vi.fn();

    render(<SubmissionForm onResult={onResult} />);
    await user.click(screen.getByRole("button", { name: "제출하기" }));

    expect(screen.getByText("내용을 입력해주세요.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(onResult).not.toHaveBeenCalled();
  });

  it("submits the entered text and reports the generated result", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "abc123",
        result: "생성된 결과입니다",
        createdAt: "2026-01-01T00:00:00.000Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onResult = vi.fn();

    render(<SubmissionForm onResult={onResult} />);
    await user.type(
      screen.getByPlaceholderText("AI에게 요청할 내용을 입력하세요"),
      "블로그 글 초안 작성해줘"
    );
    await user.click(screen.getByRole("button", { name: "제출하기" }));

    await waitFor(() => expect(onResult).toHaveBeenCalledTimes(1));
    expect(onResult).toHaveBeenCalledWith(
      expect.objectContaining({
        input: "블로그 글 초안 작성해줘",
        output: "생성된 결과입니다",
      })
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/generate",
      expect.objectContaining({ method: "POST" })
    );
  });
});
