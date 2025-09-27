#!/bin/bash
echo "Testing API endpoints sequentially..."

endpoints=(
    "/api/crypto/prices?limit=20"
    "/api/crypto/trending?limit=12"
    "/api/crypto/portfolio/balance"
    "/api/crypto/market/status"
)

success_count=0
total_count=${#endpoints[@]}

for endpoint in "${endpoints[@]}"; do
    echo -n "Testing $endpoint: "
    if curl -s "http://localhost:8000$endpoint" | grep -q '"success":true'; then
        echo "✓ SUCCESS"
        ((success_count++))
    else
        echo "✗ FAILED"
    fi
done

echo "Results: $success_count/$total_count endpoints working"