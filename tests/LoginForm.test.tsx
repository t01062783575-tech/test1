import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import LoginForm from "@/components/LoginForm";

describe("LoginForm", () => {
  beforeEach(() => {
    pushMock.mockClear();
    localStorage.clear();
    document.cookie = "workspace_session=; path=/; max-age=0";
  });

  it("blocks submission when a field is left empty", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(
      screen.getByText(/아이디와 비밀번호를 모두 입력해주세요/)
    ).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("navigates to the workspace after entering credentials", async () => {
    const user = userEvent.setup();
    render(<LoginForm />);

    await user.type(screen.getByLabelText("아이디"), "tester");
    await user.type(screen.getByLabelText("비밀번호"), "password");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(pushMock).toHaveBeenCalledWith("/workspace");
  });
});
