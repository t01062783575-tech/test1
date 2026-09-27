// 서버 없이 HTML 파일 하나로 여는 버전의 진입점 (npm run build:standalone)
import { createRoot } from "react-dom/client";
import Planner from "@/components/Planner";
import "@/app/globals.css";

createRoot(document.getElementById("root")!).render(<Planner />);
