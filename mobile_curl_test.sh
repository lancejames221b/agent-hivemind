#!/bin/bash

echo "🔍 Testing mobile login simulation..."

# Mobile user agent (iPhone)
MOBILE_UA="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"

echo "📱 Step 1: Testing mobile login page access..."
LOGIN_PAGE=$(curl -s -H "User-Agent: $MOBILE_UA" http://localhost:8900/admin/login.html)
if echo "$LOGIN_PAGE" | grep -q "hAIveMind Admin - Login"; then
    echo "✅ Mobile login page accessible"
else
    echo "❌ Mobile login page not accessible"
    exit 1
fi

echo "🔐 Step 2: Testing mobile login API..."
LOGIN_RESPONSE=$(curl -s -X POST \
    -H "User-Agent: $MOBILE_UA" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' \
    http://localhost:8900/api/v1/auth/login)

if echo "$LOGIN_RESPONSE" | grep -q '"status":"success"'; then
    echo "✅ Mobile login API successful"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
    echo "🔑 Token obtained: ${TOKEN:0:20}..."
else
    echo "❌ Mobile login API failed"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "🔍 Step 3: Testing mobile token verification..."
VERIFY_RESPONSE=$(curl -s \
    -H "User-Agent: $MOBILE_UA" \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:8900/admin/api/verify)

if echo "$VERIFY_RESPONSE" | grep -q '"status":"valid"'; then
    echo "✅ Mobile token verification successful"
else
    echo "❌ Mobile token verification failed"
    echo "Response: $VERIFY_RESPONSE"
    exit 1
fi

echo "📊 Step 4: Testing mobile dashboard access..."
DASHBOARD_PAGE=$(curl -s -H "User-Agent: $MOBILE_UA" http://localhost:8900/admin/dashboard.html)
if echo "$DASHBOARD_PAGE" | grep -q "hAIveMind Admin - Dashboard"; then
    echo "✅ Mobile dashboard accessible"
else
    echo "❌ Mobile dashboard not accessible"
    exit 1
fi

echo ""
echo "🎉 All mobile tests passed!"
echo "📱 Mobile login flow working correctly"
echo "🔐 Authentication working on mobile"
echo "📊 Dashboard accessible on mobile"