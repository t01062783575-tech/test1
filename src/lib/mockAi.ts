const TEMPLATES = [
  (input: string) => `"${input}"에 대한 초안입니다. 핵심 포인트를 3개로 정리하면: 문제 정의, 제안, 기대 효과입니다.`,
  (input: string) => `요청하신 "${input}" 내용을 바탕으로 더 간결하고 명확한 버전을 만들어봤어요.`,
  (input: string) => `"${input}"을(를) 참고해 다른 톤으로 다시 작성한 결과입니다.`,
];

export function mockGenerate(input: string): string {
  const template = TEMPLATES[input.length % TEMPLATES.length];
  return template(input.trim());
}
