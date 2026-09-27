// 서버 없이 더블클릭으로 여는 단일 HTML 파일을 만든다: dist/나의-플래너.html
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { build } from "esbuild";

mkdirSync("dist", { recursive: true });

const js = await build({
  entryPoints: ["standalone/main.tsx"],
  bundle: true,
  minify: true,
  format: "iife",
  jsx: "automatic",
  alias: { "@": "./src" },
  define: { "process.env.NODE_ENV": '"production"' },
  loader: { ".css": "empty" },
  write: false,
});

execFileSync("npx", ["@tailwindcss/cli", "-i", "src/app/globals.css", "-o", "dist/app.css", "--minify"], { stdio: "inherit" });
const css = readFileSync("dist/app.css", "utf8");
const icon = encodeURIComponent(readFileSync("src/app/icon.svg", "utf8").trim());
const code = js.outputFiles[0].text.replaceAll("</script", "<\\/script");

// src/app/layout.tsx의 테마 스크립트와 같다
const themeScript = `(function(){try{var t="system";var raw=localStorage.getItem("personal-planner:v1");if(raw){var s=JSON.parse(raw).settings;if(s&&s.theme)t=s.theme}if(t==="system")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

writeFileSync(
  "dist/나의-플래너.html",
  `<!doctype html>
<html lang="ko" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>나의 플래너</title>
<link rel="icon" href="data:image/svg+xml,${icon}">
<script>${themeScript}</script>
<style>:root{--font-geist-sans:system-ui;--font-geist-mono:ui-monospace,monospace}html,body,#root{height:100%}</style>
<style>${css}</style>
</head>
<body class="h-full font-sans antialiased">
<div id="root"></div>
<script>${code}</script>
</body>
</html>
`,
);
console.log("dist/나의-플래너.html 생성 완료");
