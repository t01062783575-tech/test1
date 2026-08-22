# ---- 여기 값만 채우세요 ----
$VERCEL_TOKEN = "여기에_Vercel_토큰_붙여넣기"
$GITHUB_REPO = "t01062783575-tech/test1"
$TEAM_ID = ""
$SUPABASE_URL = "https://프로젝트ID.supabase.co"
$SUPABASE_ANON_KEY = "여기에_publishable_key_붙여넣기"
# ----------------------------

$teamQs = ""
if ($TEAM_ID -ne "") { $teamQs = "?teamId=$TEAM_ID" }

$headers = @{
    "Authorization" = "Bearer $VERCEL_TOKEN"
    "Content-Type"  = "application/json"
}

Write-Host "1) freelancer-expense-landing 프로젝트 생성..."
$body = @{
    name                        = "freelancer-expense-landing"
    framework                   = "nextjs"
    rootDirectory               = "freelancer-expense-landing"
    commandForIgnoringBuildStep = "bash scripts/vercel-ignore-build.sh"
    gitRepository               = @{
        type = "github"
        repo = $GITHUB_REPO
    }
} | ConvertTo-Json

try {
    $createResp = Invoke-RestMethod -Uri "https://api.vercel.com/v11/projects$teamQs" -Method Post -Headers $headers -Body $body
} catch {
    Write-Host "프로젝트 생성 실패. 에러 내용:"
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } else { Write-Host $_.Exception.Message }
    exit 1
}

$createResp | ConvertTo-Json -Depth 10
$projectId = $createResp.id

if (-not $projectId) {
    Write-Host "프로젝트 생성 실패. 위 응답을 확인하세요 (repo 접근 권한 문제일 수 있음)."
    exit 1
}

Write-Host "2) 환경변수 등록..."
$envVars = @{
    "SUPABASE_URL"      = $SUPABASE_URL
    "SUPABASE_ANON_KEY" = $SUPABASE_ANON_KEY
}

foreach ($key in $envVars.Keys) {
    $envBody = @{
        key    = $key
        value  = $envVars[$key]
        type   = "encrypted"
        target = @("production", "preview", "development")
    } | ConvertTo-Json

    try {
        $envResp = Invoke-RestMethod -Uri "https://api.vercel.com/v10/projects/$projectId/env$teamQs" -Method Post -Headers $headers -Body $envBody
        Write-Host "$key 등록 완료"
    } catch {
        Write-Host "$key 등록 실패:"
        if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message } else { Write-Host $_.Exception.Message }
    }
}

Write-Host "완료! https://vercel.com/dashboard 에서 확인하세요."
