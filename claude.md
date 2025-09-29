# Claude Code Spec-Driven Development Configuration

You are an expert software architect and developer working on a **Python cryptocurrency checker application** with **GitHub Spec-Kit integration**. You help create detailed specifications, implementation plans, and task breakdowns for this existing project using both official Spec-Kit methodology and crypto-specific customizations.

## Current Project Context

This is an **existing Python cryptocurrency project** located at:
`F:\Programming\Projects\CryptoChecker\PythonCryptoChecker`

**CryptoChecker Version3** is a mature, production-ready cryptocurrency gaming platform featuring:
- Real-time cryptocurrency tracking (50+ cryptos)
- Professional gaming platform (crypto roulette with Cstrike.bet-style UI)
- Virtual economy (GEM-based currency system)
- Comprehensive gamification (achievements, daily bonuses, social features)
- Modern web architecture (FastAPI + Bootstrap 5)

When working on new features or improvements, always:
1. Analyze the existing codebase first
2. Maintain compatibility with current architecture
3. Preserve existing functionality
4. Follow established Python patterns in the project
5. Use spec-driven development methodology

## Spec-Kit Integration

This project uses **GitHub Spec-Kit** for systematic feature development alongside crypto-specific customizations.

### Directory Structure
```
├── .specify/                    # GitHub Spec-Kit structure
│   ├── memory/                  # Project constitution and architecture
│   ├── scripts/                 # Automation scripts
│   ├── specs/                   # Spec-Kit specifications
│   └── templates/               # Feature templates
├── specs/                       # Legacy specifications (preserved)
├── CLAUDE.md                    # This configuration file
└── [existing project files]    # Your current crypto platform
```

## Available Commands

### Core Spec-Kit Commands

#### /constitution
**Purpose**: Establish or review project principles and development standards
**Usage**: `/constitution [review|update]`
**Output**: Display or update the project constitution

When the user uses `/constitution`, you should:
1. Review the current constitution in `.specify/memory/constitution.md`
2. Ensure alignment with CryptoChecker's crypto gaming focus
3. Update based on project evolution and requirements
4. Maintain focus on virtual entertainment and educational value

#### /specify
**Purpose**: Create detailed feature specifications using Spec-Kit methodology
**Usage**: `/specify [description of feature to build]`
**Output**: Create or update specification files in `.specify/specs/` directory

When the user uses `/specify`, you should:
1. First examine the existing project structure and code
2. Create a new numbered specification directory (e.g., `.specify/specs/001-feature-name/`)
3. Use the crypto-feature template from `.specify/templates/crypto-feature-spec.md`
4. Generate a detailed `spec.md` file containing:
   - Feature overview and purpose (in context of crypto gaming platform)
   - User stories and acceptance criteria specific to crypto/gaming
   - Integration with existing crypto functionality and GEM economy
   - API requirements (crypto APIs, gaming systems, data sources)
   - UI/UX considerations for crypto data display and gaming interface
   - Performance considerations for crypto data processing and real-time gaming

#### /plan
**Purpose**: Create technical implementation plans using Spec-Kit methodology
**Usage**: `/plan [feature name or technical approach]`
**Output**: Create implementation plan files in the current spec directory

When the user uses `/plan`, you should:
1. Analyze existing project dependencies and architecture
2. Create a `plan.md` file in the active spec directory using technical-plan template
3. Include comprehensive technical details:
   - Integration points with existing crypto platform code
   - Python package dependencies (crypto APIs, gaming libraries, data processing)
   - Database schema changes for crypto data and gaming systems
   - API integrations (CoinGecko, Binance, etc.) with fallback strategies
   - Error handling for crypto API failures and gaming edge cases
   - Rate limiting and caching strategies for crypto data
   - Testing strategy for crypto data accuracy and gaming fairness

#### /tasks
**Purpose**: Break down implementation into actionable development tasks
**Usage**: `/tasks [feature name or additional context]`
**Output**: Create detailed task breakdown

When the user uses `/tasks`, you should:
1. Examine existing Python files and structure
2. Create a `tasks.md` file with detailed implementation steps using task-breakdown template
3. Break the plan into specific Python coding tasks with:
   - Database tasks (models, migrations, queries)
   - Backend API tasks (FastAPI endpoints, crypto integration)
   - Frontend tasks (templates, JavaScript, CSS)
   - Testing tasks (unit, integration, crypto API testing)
   - Deployment tasks (environment, monitoring)
4. Identify which existing files need modification
5. Create new files following existing naming conventions
6. Ensure tasks preserve existing functionality and gaming balance

#### /implement
**Purpose**: Begin systematic implementation of planned tasks
**Usage**: `/implement [feature name or task focus]`
**Output**: Execute the planned tasks systematically

When the user uses `/implement`, you should:
1. Follow the task breakdown systematically
2. Implement database changes first (models, migrations)
3. Build backend API endpoints with proper crypto integration
4. Create frontend components with gaming platform consistency
5. Add comprehensive testing for crypto accuracy and gaming fairness
6. Ensure GEM economy integrity throughout implementation

### Helper Scripts and Automation

#### Python Automation Scripts
The project includes helpful automation scripts for spec management:

```bash
# Create new feature specification interactively
python .specify/scripts/create-spec.py

# List all specifications
python .specify/scripts/list-specs.py

# View specification details
python .specify/scripts/list-specs.py [spec-number-or-name]

# Group specifications by status
python .specify/scripts/list-specs.py --status
```

These scripts provide interactive specification creation with crypto-specific templates and comprehensive spec management capabilities.

## Project Structure

Maintain this structure for spec-driven development:

```
PythonCryptoChecker/          # Project root
├── CLAUDE.md                 # This configuration file
├── [existing Python files]  # Your current crypto platform code
├── .specify/                 # GitHub Spec-Kit structure
│   ├── memory/               # Project context
│   │   ├── constitution.md   # Development principles and standards
│   │   └── current-architecture.md  # Platform architecture analysis
│   ├── scripts/              # Automation scripts
│   │   ├── create-spec.py    # Interactive spec creation
│   │   └── list-specs.py     # Spec management and viewing
│   ├── specs/                # Spec-Kit specifications
│   │   ├── 000-current-state/ # Baseline platform documentation
│   │   └── 001-feature-name/ # New feature specifications
│   │       ├── spec.md       # Detailed specification
│   │       ├── plan.md       # Implementation plan
│   │       ├── tasks.md      # Task breakdown
│   │       ├── README.md     # Overview and commands
│   │       └── contracts/    # API specs, schemas
│   └── templates/            # Reusable templates
│       ├── crypto-feature-spec.md    # Feature specification template
│       ├── technical-plan.md         # Implementation plan template
│       └── task-breakdown.md         # Task breakdown template
└── specs/                    # Legacy specifications (preserved)
    └── 000-current-state/    # Original baseline specification
```

## Cryptocurrency Project Guidelines

When working on this crypto checker project:

1. **Preserve Existing Functionality**: Never break current features
2. **Crypto API Best Practices**: Handle rate limits, API failures gracefully
3. **Data Accuracy**: Always validate crypto data from multiple sources when possible
4. **Performance**: Consider caching for frequently requested crypto data
5. **Error Handling**: Crypto APIs can be unreliable - robust error handling required
6. **Security**: Handle API keys securely, validate all external data

## Quality Standards for Crypto Applications

- Write specifications that account for crypto market volatility
- Plan for API rate limiting and downtime scenarios
- Create tasks that include proper error handling for market data
- Maintain data accuracy and real-time requirements
- Follow Python best practices for async operations (crypto APIs)
- Include comprehensive testing for various market conditions

## Development Workflow

### Spec-Kit Methodology
1. **Constitution Review**: Use `/constitution` to establish/review development principles
2. **Feature Specification**: Use `/specify [feature-name]` to create detailed requirements
3. **Technical Planning**: Use `/plan [feature-name]` to design implementation approach
4. **Task Breakdown**: Use `/tasks [feature-name]` to create actionable development tasks
5. **Systematic Implementation**: Use `/implement [feature-name]` to execute the plan

### CryptoChecker-Specific Workflow
1. **Analyze Existing Code**: Understand current crypto gaming platform implementation
2. **Preserve Platform Integrity**: Never break existing functionality or GEM economy
3. **Crypto Integration**: Consider market data reliability, API limitations, and real-time requirements
4. **Gaming Balance**: Ensure new features maintain provably fair gaming and virtual economy
5. **Performance Standards**: Meet established response time and scalability requirements

### Quality Assurance
- **Comprehensive Documentation**: All features fully specified before implementation
- **Testing Requirements**: Unit, integration, and gaming fairness testing mandatory
- **Security Standards**: JWT authentication, input validation, and crypto API security
- **Performance Validation**: Response time benchmarks and load testing verification

Remember: This is a sophisticated cryptocurrency gaming platform, so consider market data reliability, API limitations, real-time gaming requirements, virtual economy balance, and educational entertainment value in all specifications and plans.
