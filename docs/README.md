# CryptoChecker Documentation

## 📁 Documentation Structure

### `/guides/` - Development Guides
Permanent guides for developers working on CryptoChecker:
- **DEVELOPER_GUIDE.md** - Complete development setup and workflow
- **TESTING_GUIDE.md** - Testing strategies and test writing
- **DEPLOYMENT.md** - Deployment procedures and environments
- **CONTRIBUTING.md** - How to contribute to the project
- **COLLABORATIVE_SETUP.md** - Team collaboration guidelines
- **VISUAL_ENHANCEMENT_GUIDE.md** - UI/UX design guidelines

### `/specs/` - Technical Specifications
Feature specifications and architectural decisions:
- **GAMIFICATION_PLAN.md** - Gamification system design
- **ROULETTE_SYSTEM.md** - Roulette gaming system architecture
- **CSTRIKE_ROULETTE_RESEARCH.md** - Research and inspiration from CS:GO betting sites

### `/session-reports/` - Development Session Reports
Temporary reports from development sessions (auto-archived):
- **CLICKER_*.md** - Clicker game development progress
- **PHASE*.md** - Multi-phase feature development reports
- **SESSION_SUMMARY.md** - Session completion summaries
- **GEM_MARKETPLACE_*.md** - GEM economy implementation reports
- **STOCK_TRADING_*.md** - Stock trading feature reports

### `/archive/` - Historical Documentation
Old documentation, bug fixes, and deprecated content:
- Bug fix reports
- Enhancement summaries
- Deprecated guides
- Historical project summaries

---

## 📝 Root-Level Documentation (Project Root)

These are the **only** .md files that should remain in the project root:

- **README.md** - Main project README with setup instructions
- **CLAUDE.md** - Claude Code spec-driven development configuration
- **CHANGELOG.md** - Version history and release notes
- **API_DOCUMENTATION.md** - API reference documentation
- **PROJECT_OVERVIEW.md** - High-level project architecture
- **PROJECT_STATUS.md** - Current project status and roadmap
- **README_DB.md** - Database setup instructions

---

## 🗂️ Documentation Guidelines

### When Creating New Documentation:

1. **Session Reports** → Save to `/docs/session-reports/`
   - Format: `FEATURE_NAME_PROGRESS.md`, `FEATURE_NAME_COMPLETE.md`
   - These are temporary and can be archived after 30 days

2. **Permanent Guides** → Save to `/docs/guides/`
   - Development processes, testing, deployment
   - Keep these updated and current

3. **Feature Specs** → Save to `/docs/specs/` or `.specify/specs/`
   - Technical specifications for features
   - Architecture decisions

4. **Temporary/Deprecated** → Move to `/docs/archive/`
   - Old bug fix reports
   - Deprecated documentation
   - Historical summaries

### Auto-Ignore Patterns (in `.gitignore`):

Session reports created in the root directory will be automatically ignored:
- `CLICKER_*.md`
- `PHASE*.md`
- `*_COMPLETE.md`
- `*_PROGRESS.md`
- `*_FIXED.md`

**Move these to `/docs/session-reports/` to track them in git.**

---

## 🧹 Keeping Documentation Clean

Run this command periodically to organize new files:

```bash
# Move session reports
mv CLICKER_*.md PHASE*.md SESSION_*.md docs/session-reports/ 2>/dev/null

# Move new guides (if any)
mv *GUIDE.md DEPLOYMENT.md CONTRIBUTING.md docs/guides/ 2>/dev/null

# Archive old files
mv *FIX*.md *SUMMARY*.md docs/archive/ 2>/dev/null
```

---

**Last Updated**: 2025-10-21
**Structure Version**: 2.0
