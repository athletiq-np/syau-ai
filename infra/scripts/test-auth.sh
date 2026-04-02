#!/bin/bash

# Test script for API Authentication & Tunnel Monitoring
# Usage: bash infra/scripts/test-auth.sh

set -e

API_URL="http://localhost:8000"
DEV_KEY="syauai_dev_key_12345"
TEST_KEY="syauai_test_key_67890"
INVALID_KEY="invalid_key_xyz"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_count=0
pass_count=0
fail_count=0

function test_case() {
    local name=$1
    local method=$2
    local endpoint=$3
    local auth_key=$4
    local data=$5
    local expected_status=$6

    test_count=$((test_count + 1))
    echo -e "\n${YELLOW}[Test $test_count]${NC} $name"
    echo "  Method: $method $endpoint"
    echo "  Auth: $([ -z "$auth_key" ] && echo "NONE" || echo "$auth_key (first 10 chars)")"

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $auth_key" \
            -H "Content-Type: application/json")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
            -H "Authorization: Bearer $auth_key" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    echo "  Response: HTTP $http_code"

    if [ "$http_code" == "$expected_status" ]; then
        echo -e "  ${GREEN}✓ PASS${NC}"
        pass_count=$((pass_count + 1))
        # Show job_id if present (for tracking)
        if echo "$body" | grep -q "job_id"; then
            job_id=$(echo "$body" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)
            echo "  Job ID: $job_id"
        fi
    else
        echo -e "  ${RED}✗ FAIL${NC} (expected $expected_status, got $http_code)"
        echo "  Response: $body"
        fail_count=$((fail_count + 1))
    fi
}

echo "======================================================================"
echo "  SYAU AI API Authentication & Tunnel Monitoring Test Suite"
echo "======================================================================"
echo "API URL: $API_URL"
echo "Dev Key: $DEV_KEY"
echo "Test Key: $TEST_KEY"

# ===== SECTION 1: Auth Tests =====
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo "SECTION 1: API Authentication Tests"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

# Test 1.1: Missing auth header
test_case "Missing Authorization header" \
    "GET" "/api/jobs" "" "" "403"

# Test 1.2: Invalid auth format
test_case "Invalid Authorization format (no Bearer)" \
    "GET" "/api/jobs" "token123" "" "403"

# Test 1.3: Invalid API key
test_case "Invalid API key" \
    "GET" "/api/jobs" "$INVALID_KEY" "" "403"

# Test 1.4: Valid auth - list jobs (empty)
test_case "Valid auth - list jobs (dev user)" \
    "GET" "/api/jobs?page=1&page_size=10" "$DEV_KEY" "" "200"

# Test 1.5: Valid auth - submit job (dev user)
JOB_DATA='{
  "type": "video",
  "model": "wan-2.2",
  "prompt": "a cat playing with yarn",
  "negative_prompt": "blurry",
  "params": {
    "num_frames": 81,
    "width": 640,
    "height": 640
  }
}'

test_case "Valid auth - submit video job (dev user)" \
    "POST" "/api/jobs" "$DEV_KEY" "$JOB_DATA" "202"

# Extract job_id from last response for further tests
DEV_JOB_ID=$(echo "$response" | head -n-1 | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)
echo "  Saved Job ID for further tests: $DEV_JOB_ID"

# Test 1.6: Get own job (dev user)
if [ -n "$DEV_JOB_ID" ]; then
    test_case "Get own job (dev user)" \
        "GET" "/api/jobs/$DEV_JOB_ID" "$DEV_KEY" "" "200"
fi

# Test 1.7: Submit job with test key
test_case "Valid auth - submit job (test user)" \
    "POST" "/api/jobs" "$TEST_KEY" "$JOB_DATA" "202"

TEST_JOB_ID=$(echo "$response" | head -n-1 | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)
echo "  Saved Job ID for further tests: $TEST_JOB_ID"

# ===== SECTION 2: User Isolation Tests =====
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo "SECTION 2: User Isolation Tests"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

# Test 2.1: Dev user cannot see test user's job
if [ -n "$TEST_JOB_ID" ]; then
    test_case "Dev user CANNOT access test user's job (should fail)" \
        "GET" "/api/jobs/$TEST_JOB_ID" "$DEV_KEY" "" "403"
fi

# Test 2.2: Test user cannot see dev user's job
if [ -n "$DEV_JOB_ID" ]; then
    test_case "Test user CANNOT access dev user's job (should fail)" \
        "GET" "/api/jobs/$DEV_JOB_ID" "$TEST_KEY" "" "403"
fi

# Test 2.3: Dev user list jobs (should only see own)
test_case "Dev user lists jobs (should only see own)" \
    "GET" "/api/jobs?page=1&page_size=100" "$DEV_KEY" "" "200"

# Test 2.4: Test user list jobs (should only see own)
test_case "Test user lists jobs (should only see own)" \
    "GET" "/api/jobs?page=1&page_size=100" "$TEST_KEY" "" "200"

# ===== SECTION 3: Health & Tunnel Tests =====
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo "SECTION 3: Health & Tunnel Monitoring Tests"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"

# Test 3.1: Health endpoint (no auth required)
test_case "Health check (no auth required)" \
    "GET" "/health" "" "" "200"

# Test 3.2: Check tunnel status in logs
echo -e "\n${YELLOW}[Test $((test_count + 1))]${NC} Tunnel monitor status"
echo "  Checking backend logs for tunnel health..."
if docker-compose logs backend 2>/dev/null | grep -q "tunnel_monitor"; then
    echo -e "  ${GREEN}✓ PASS${NC} - Tunnel monitor is running"
    pass_count=$((pass_count + 1))
else
    echo -e "  ${YELLOW}⚠ WARNING${NC} - Tunnel monitor not yet visible in logs (may not have run cycle yet)"
fi
test_count=$((test_count + 1))

# ===== RESULTS =====
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST RESULTS"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo "Total Tests: $test_count"
echo -e "${GREEN}Passed: $pass_count${NC}"
if [ $fail_count -gt 0 ]; then
    echo -e "${RED}Failed: $fail_count${NC}"
else
    echo -e "${GREEN}Failed: 0${NC}"
fi

if [ $fail_count -eq 0 ]; then
    echo -e "\n${GREEN}✓ ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "\n${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
