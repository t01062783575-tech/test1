#!/usr/bin/env bash
set -euo pipefail

# ---- 여기 값만 채우세요 ----
VERCEL_TOKEN="새로_발급받은_토큰"
GITHUB_REPO="t01062783575-tech/test1"
TEAM_ID=""   # 팀 계정이면 Vercel 팀 설정의 Team ID, 개인 계정이면 빈 값 유지
SUPABASE_URL="https://xxxx.supabase.co"
SUPABASE_ANON_KEY="xxxx"
# ----------------------------

TEAM_QS=""
if [ -n "$TEAM_ID" ]; then TEAM_QS="?teamId=$TEAM_ID"; fi

echo "1) freelancer-expense-landing 프로젝트 생성..."
CREATE_RESP=$(curl -sS -X POST "https://api.vercel.com/v11/projects${TEAM_QS}" \
  -H "Authorization: Bearer $VERCEL_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"freelancer-expense-landing\",
    \"framework\": \"nextjs\",
    \"rootDirectory\": \"freelancer-expense-landing\",
    \"commandForIgnoringBuildStep\": \"bash scripts/vercel-ignore-build.sh\",
    \"gitRepository\": { \"type\": \"github\", \"repo\": \"$GITHUB_REPO\" }
  }")

echo "$CREATE_RESP" | jq .
PROJECT_ID=$(echo "$CREATE_RESP" | jq -r '.id')

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "null" ]; then
  echo "프로젝트 생성 실패. 위 응답 메시지를 확인하세요 (repo 접근 권한 문제일 수 있음)."
  exit 1
fi

echo "2) 환경변수 등록..."
for KV in "SUPABASE_URL=$SUPABASE_URL" "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY"; do
  KEY="${KV%%=*}"
  VALUE="${KV#*=}"
  curl -sS -X POST "https://api.vercel.com/v10/projects/${PROJECT_ID}/env${TEAM_QS}" \
    -H "Authorization: Bearer $VERCEL_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"key\":\"$KEY\",\"value\":\"$VALUE\",\"type\":\"encrypted\",\"target\":[\"production\",\"preview\",\"development\"]}" | jq -c '{key: .key, target: .target} // .'
done

echo "완료! https://vercel.com/dashboard 에서 확인하세요."
