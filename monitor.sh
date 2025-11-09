#!/bin/bash
# Простой мониторинг Auth Service v2

BASE_URL="http://localhost:8000"
ADMIN_USER="admin"
ADMIN_PASS="admin123"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          AUTH SERVICE V2 - MONITORING DASHBOARD               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🕐 Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Health Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 HEALTH STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HEALTH=$(curl -s $BASE_URL/health)
STATUS=$(echo $HEALTH | jq -r '.status')
DB_STATUS=$(echo $HEALTH | jq -r '.database')
VERSION=$(echo $HEALTH | jq -r '.version')
ENV=$(echo $HEALTH | jq -r '.environment')

if [ "$STATUS" == "healthy" ]; then
    echo "✅ Service Status:  $STATUS"
else
    echo "❌ Service Status:  $STATUS"
fi

if [ "$DB_STATUS" == "connected" ]; then
    echo "✅ Database:        $DB_STATUS"
else
    echo "❌ Database:        $DB_STATUS"
fi

echo "📦 Version:         $VERSION"
echo "🌍 Environment:     $ENV"
echo ""

# Statistics
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 STATISTICS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

STATS=$(curl -s -u $ADMIN_USER:$ADMIN_PASS $BASE_URL/admin/statistics)
TOTAL_USERS=$(echo $STATS | jq -r '.total_users')
ACTIVE_USERS=$(echo $STATS | jq -r '.active_users')
WHITELIST=$(echo $STATS | jq -r '.whitelisted_users')
TOTAL_WHITELIST=$(echo $STATS | jq -r '.total_whitelist_entries')

echo "👥 Total Users:           $TOTAL_USERS"
echo "✅ Active Users:          $ACTIVE_USERS"
echo "📋 Whitelisted (active):  $WHITELIST"
echo "📋 Whitelist (total):     $TOTAL_WHITELIST"
echo ""

# Whitelist Preview
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 WHITELIST PREVIEW (last 5)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

curl -s -u $ADMIN_USER:$ADMIN_PASS "$BASE_URL/admin/whitelist?limit=5" | \
  jq -r '.allowed_users[] | "  • User ID: \(.hh_user_id) - \(.description) (by \(.added_by))"'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔗 ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Service:      $BASE_URL"
echo "  Health:       $BASE_URL/health"
echo "  OpenAPI:      $BASE_URL/openapi.json"
echo ""
echo "💡 Tip: Run with 'watch -n 5 ./monitor.sh' for live updates"
echo ""
