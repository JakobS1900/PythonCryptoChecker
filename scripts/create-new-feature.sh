#!/bin/bash
# Create new feature specification for CryptoChecker

if [[ -z "$1" ]]; then
    echo "Usage: $0 <feature-name>"
    echo "Example: $0 portfolio-tracker"
    exit 1
fi

FEATURE_NAME="$1"
SPEC_NUMBER=$(printf "%03d" $(($(ls specs/ 2>/dev/null | wc -l) + 1)))
SPEC_DIR="specs/${SPEC_NUMBER}-${FEATURE_NAME}"

mkdir -p "$SPEC_DIR/contracts"

echo "Created specification directory: $SPEC_DIR"
echo ""
echo "Next steps:"
echo "1. Open Claude Code in this project"
echo "2. Use: /specify [describe the $FEATURE_NAME feature]"
echo "3. Use: /plan [technical approach for $FEATURE_NAME]"
echo "4. Use: /tasks [implement $FEATURE_NAME]"
