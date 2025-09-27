#!/bin/bash
# Show CryptoChecker project status

echo "🚀 CryptoChecker Project Status"
echo "==============================="
echo ""
echo "📁 Project Location: $PWD"
echo ""
echo "📋 Specifications:"
if [[ -d specs && $(ls specs/ 2>/dev/null | wc -l) -gt 0 ]]; then
    ls -la specs/
else
    echo "  No specifications yet - use /specify in Claude Code to create them"
fi
echo ""
echo "📄 Available Scripts:"
ls -la scripts/ 2>/dev/null || echo "  No scripts directory"
echo ""
echo "🎯 To add new features:"
echo "  1. cd to this directory"
echo "  2. claude-code ."
echo "  3. Use /specify, /plan, /tasks commands"
