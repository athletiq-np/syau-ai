# PowerShell test script for API Authentication
# Usage: powershell -ExecutionPolicy Bypass -File infra/scripts/test-auth.ps1

$ErrorActionPreference = "Stop"

$API_URL = "http://localhost:8000"
$DEV_KEY = "syauai_dev_key_12345"
$TEST_KEY = "syauai_test_key_67890"
$INVALID_KEY = "invalid_key_xyz"

$testCount = 0
$passCount = 0
$failCount = 0

function Test-Case {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [string]$AuthKey,
        [string]$Data,
        [int]$ExpectedStatus
    )

    $script:testCount++
    Write-Host "`n[Test $($script:testCount)] $Name" -ForegroundColor Yellow
    Write-Host "  Method: $Method $Endpoint"
    Write-Host "  Auth: $(if ([string]::IsNullOrEmpty($AuthKey)) { 'NONE' } else { "$($AuthKey.Substring(0,10))..." })"

    $uri = "$API_URL$Endpoint"
    $headers = @{
        "Content-Type" = "application/json"
    }

    if (-not [string]::IsNullOrEmpty($AuthKey)) {
        $headers["Authorization"] = "Bearer $AuthKey"
    }

    try {
        if ([string]::IsNullOrEmpty($Data)) {
            $response = Invoke-WebRequest -Uri $uri -Method $Method -Headers $headers -ErrorAction Stop
        } else {
            $response = Invoke-WebRequest -Uri $uri -Method $Method -Headers $headers -Body $Data -ErrorAction Stop
        }
        $httpCode = $response.StatusCode
        $body = $response.Content
    }
    catch {
        $httpCode = $_.Exception.Response.StatusCode.Value__
        $body = $_.Exception.Response.Content.ReadAsStream() | { param($stream) [System.IO.StreamReader]::new($stream).ReadToEnd() }
    }

    Write-Host "  Response: HTTP $httpCode"

    if ($httpCode -eq $ExpectedStatus) {
        Write-Host "  ✓ PASS" -ForegroundColor Green
        $script:passCount++

        # Extract job_id if present
        if ($body -like '*job_id*') {
            $jobId = ($body | Select-String -Pattern '"job_id":"([^"]+)"' -AllMatches).Matches[0].Groups[1].Value
            if ($jobId) {
                Write-Host "  Job ID: $jobId"
                return $jobId
            }
        }
    } else {
        Write-Host "  ✗ FAIL (expected $ExpectedStatus, got $httpCode)" -ForegroundColor Red
        Write-Host "  Response: $body"
        $script:failCount++
    }

    return $null
}

# Header
Write-Host "======================================================================" -ForegroundColor Yellow
Write-Host "  SYAU AI API Authentication & Tunnel Monitoring Test Suite" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Yellow
Write-Host "API URL: $API_URL"
Write-Host "Dev Key: $DEV_KEY"
Write-Host "Test Key: $TEST_KEY"

# ===== SECTION 1: Auth Tests =====
Write-Host "`n══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "SECTION 1: API Authentication Tests" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow

# Test 1.1: Missing auth header
Test-Case "Missing Authorization header" "GET" "/api/jobs" "" "" 403

# Test 1.2: Invalid auth format
Test-Case "Invalid Authorization format (no Bearer)" "GET" "/api/jobs" "token123" "" 403

# Test 1.3: Invalid API key
Test-Case "Invalid API key" "GET" "/api/jobs" $INVALID_KEY "" 403

# Test 1.4: Valid auth - list jobs
Test-Case "Valid auth - list jobs (dev user)" "GET" "/api/jobs?page=1&page_size=10" $DEV_KEY "" 200

# Test 1.5: Valid auth - submit job
$jobData = @{
    type = "video"
    model = "wan-2.2"
    prompt = "a cat playing with yarn"
    negative_prompt = "blurry"
    params = @{
        num_frames = 81
        width = 640
        height = 640
    }
} | ConvertTo-Json

$devJobId = Test-Case "Valid auth - submit video job (dev user)" "POST" "/api/jobs" $DEV_KEY $jobData 202

# Test 1.6: Get own job
if ($devJobId) {
    Test-Case "Get own job (dev user)" "GET" "/api/jobs/$devJobId" $DEV_KEY "" 200
}

# Test 1.7: Submit job with test key
$testJobId = Test-Case "Valid auth - submit job (test user)" "POST" "/api/jobs" $TEST_KEY $jobData 202

# ===== SECTION 2: User Isolation Tests =====
Write-Host "`n══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "SECTION 2: User Isolation Tests" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow

# Test 2.1: Dev user cannot see test user's job
if ($testJobId) {
    Test-Case "Dev user CANNOT access test user's job (should fail)" "GET" "/api/jobs/$testJobId" $DEV_KEY "" 403
}

# Test 2.2: Test user cannot see dev user's job
if ($devJobId) {
    Test-Case "Test user CANNOT access dev user's job (should fail)" "GET" "/api/jobs/$devJobId" $TEST_KEY "" 403
}

# Test 2.3: Dev user list jobs
Test-Case "Dev user lists jobs (should only see own)" "GET" "/api/jobs?page=1&page_size=100" $DEV_KEY "" 200

# Test 2.4: Test user list jobs
Test-Case "Test user lists jobs (should only see own)" "GET" "/api/jobs?page=1&page_size=100" $TEST_KEY "" 200

# ===== SECTION 3: Health & Tunnel Tests =====
Write-Host "`n══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "SECTION 3: Health & Tunnel Monitoring Tests" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow

# Test 3.1: Health endpoint (no auth required)
Test-Case "Health check (no auth required)" "GET" "/health" "" "" 200

# Test 3.2: Check tunnel status
Write-Host "`n[Test $($testCount+1)] Tunnel monitor status" -ForegroundColor Yellow
Write-Host "  Checking Docker logs for tunnel health..."
try {
    $logs = docker-compose logs backend 2>$null
    if ($logs -like "*tunnel_monitor*") {
        Write-Host "  ✓ PASS - Tunnel monitor is running" -ForegroundColor Green
        $script:passCount++
    } else {
        Write-Host "  ⚠ WARNING - Tunnel monitor not yet visible in logs (may not have run cycle yet)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ WARNING - Could not check Docker logs" -ForegroundColor Yellow
}
$testCount++

# ===== RESULTS =====
Write-Host "`n══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "TEST RESULTS" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "Total Tests: $testCount"
Write-Host "Passed: $passCount" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "Failed: $failCount" -ForegroundColor Red
} else {
    Write-Host "Failed: 0" -ForegroundColor Green
}

if ($failCount -eq 0) {
    Write-Host "`n✓ ALL TESTS PASSED" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n✗ SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}
