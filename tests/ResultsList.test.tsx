import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultsList from "@/components/ResultsList";

describe("ResultsList", () => {
  it("shows an empty-state message when there are no results", () => {
    render(<ResultsList results={[]} />);
    expect(screen.getByText(/아직 생성된 결과가 없어요/)).toBeInTheDocument();
  });

  it("renders each result's input and output", () => {
    render(
      <ResultsList
        results={[
          {
            id: "1",
            input: "안녕",
            output: "안녕하세요! 무엇을 도와드릴까요?",
            createdAt: new Date().toISOString(),
          },
        ]}
      />
    );

    expect(screen.getByText(/입력: 안녕/)).toBeInTheDocument();
    expect(screen.getByText(/안녕하세요! 무엇을 도와드릴까요?/)).toBeInTheDocument();
  });
});
