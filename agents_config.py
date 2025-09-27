#!/usr/bin/env python3
"""
Ultimate CryptoChecker Agents Configuration System

This module provides comprehensive agent definitions for the CryptoChecker
Python gaming platform, utilizing zen-mcp tools, deep-research capabilities,
and Gemini Flash for efficient development workflows.

Created for the production-ready CryptoChecker Gaming Platform
- Crypto Roulette System: ✅ PRODUCTION READY
- Authentication: ✅ Complete with JWT + session management  
- Virtual Economy: ✅ GEM coins with cross-component sync
- API Ecosystem: ✅ 25+ REST endpoints
- Testing Suite: ✅ 40+ test scenarios with 100% pass rate
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import os
import json

class AgentType(Enum):
    """Agent types for different development workflows"""
    TESTER = "crypto-tester"
    DEEP_DEBUGGER = "crypto-deep-debugger" 
    CONSTRUCTOR = "crypto-constructor"
    CONTEXT_KEEPER = "crypto-context-keeper"

class TaskComplexity(Enum):
    """Task complexity levels for agent selection"""
    SIMPLE = "simple"       # Basic fixes, single file changes
    MODERATE = "moderate"   # Multi-file changes, feature additions
    COMPLEX = "complex"     # System overhauls, major features
    CRITICAL = "critical"   # Production issues, security fixes

@dataclass
class AgentCapability:
    """Individual capability of an agent"""
    name: str
    description: str
    tools: List[str]
    cost_level: str  # low, medium, high
    use_cases: List[str]

@dataclass
class AgentWorkflow:
    """Workflow definition for an agent"""
    name: str
    steps: List[Dict[str, Any]]
    conditions: Dict[str, Any]
    fallback: Optional[str] = None

@dataclass
class CryptoAgent:
    """Complete agent definition for CryptoChecker platform"""
    name: str
    type: AgentType
    description: str
    purpose: str
    tools: List[str]
    capabilities: List[AgentCapability]
    workflows: List[AgentWorkflow]
    context_requirements: List[str]
    cost_profile: Dict[str, str]
    best_for: List[str]
    avoid_for: List[str]

class CryptoCheckerAgentsConfig:
    """
    Ultimate agents configuration for CryptoChecker Gaming Platform
    
    Provides intelligent agent selection and orchestration for:
    - Testing with context awareness and safe cleanup
    - Deep research debugging for complex issues
    - Construction/overhaul with zen tools
    - Documentation and context management
    """
    
    def __init__(self):
        self.agents = self._initialize_agents()
        self.project_context = self._load_project_context()
        
    def _load_project_context(self) -> Dict[str, Any]:
        """Load project context from documentation files"""
        context = {
            "platform_type": "CryptoChecker Gaming Platform",
            "status": "PRODUCTION READY",
            "core_systems": [
                "Crypto Roulette (✅ Complete)",
                "Authentication (✅ JWT + Sessions)", 
                "Virtual Economy (✅ GEM coins)",
                "API Ecosystem (✅ 25+ endpoints)",
                "Testing Suite (✅ 40+ scenarios)"
            ],
            "test_files": [
                "test_betting_fixes.py",
                "test_endpoints.py", 
                "test_roulette_fixes.py",
                "test_balance_persistence.py",
                "test_server.py"
            ],
            "critical_files": [
                "CLAUDE.md",
                "README.md",
                "main.py",
                "run_server.py"
            ],
            "documentation_files": self._get_documentation_files()
        }
        return context
    
    def _get_documentation_files(self) -> List[str]:
        """Get list of all documentation files in project"""
        docs = [
            "CLAUDE.md", "README.md", "PROJECT_OVERVIEW.md",
            "ENHANCEMENT_SUMMARY.md", "API_DOCUMENTATION.md",
            "DEVELOPER_GUIDE.md", "ROULETTE_FIXES_DOCUMENTATION.md",
            "FINAL_CRYPTO_ROULETTE_SUCCESS.md", "DOCUMENTATION_INDEX.md"
        ]
        return docs
    
    def _initialize_agents(self) -> Dict[str, CryptoAgent]:
        """Initialize all agents with comprehensive configurations"""
        return {
            AgentType.TESTER.value: self._create_testing_agent(),
            AgentType.DEEP_DEBUGGER.value: self._create_deep_debugging_agent(),
            AgentType.CONSTRUCTOR.value: self._create_construction_agent(),
            AgentType.CONTEXT_KEEPER.value: self._create_context_agent()
        }
    
    def _create_testing_agent(self) -> CryptoAgent:
        """
        Testing & Quality Assurance Agent
        
        Specialized for the CryptoChecker platform with:
        - Context awareness of README files and project structure
        - Safe test file cleanup with prerequisite detection
        - Comprehensive testing of crypto roulette system
        - Integration with existing test suite (40+ scenarios)
        """
        capabilities = [
            AgentCapability(
                name="context_aware_testing",
                description="Reads project documentation before testing",
                tools=["Read", "Glob", "mcp__zen__zen_gemini_query"],
                cost_level="low",
                use_cases=["Pre-test analysis", "Context gathering", "Documentation review"]
            ),
            AgentCapability(
                name="comprehensive_test_execution",
                description="Runs full test suites with proper validation",
                tools=["Bash", "Read", "Write"],
                cost_level="medium", 
                use_cases=["Test execution", "Result validation", "Coverage analysis"]
            ),
            AgentCapability(
                name="safe_cleanup",
                description="Intelligent cleanup with prerequisite detection",
                tools=["Grep", "Read", "Bash"],
                cost_level="low",
                use_cases=["Temporary file cleanup", "Dependency analysis", "Safe deletion"]
            ),
            AgentCapability(
                name="test_analysis",
                description="Analyzes test results using Gemini Flash",
                tools=["mcp__zen__zen_gemini_query", "Read"],
                cost_level="low",
                use_cases=["Failure analysis", "Test recommendations", "Quality metrics"]
            )
        ]
        
        workflows = [
            AgentWorkflow(
                name="comprehensive_testing",
                steps=[
                    {"action": "read_context", "tools": ["Read", "Glob"], "target": "README.md, CLAUDE.md"},
                    {"action": "analyze_tests", "tools": ["Read", "Grep"], "target": "test_*.py files"},
                    {"action": "detect_prerequisites", "tools": ["Grep", "Read"], "target": "dependency analysis"},
                    {"action": "execute_tests", "tools": ["Bash"], "target": "run test suites"},
                    {"action": "validate_results", "tools": ["Read", "mcp__zen__zen_gemini_query"], "target": "analyze outcomes"},
                    {"action": "safe_cleanup", "tools": ["Bash", "Grep"], "target": "remove temp files"}
                ],
                conditions={"requires_context": True, "cleanup_safety": True}
            )
        ]
        
        return CryptoAgent(
            name="CryptoChecker Testing & QA Agent",
            type=AgentType.TESTER,
            description="Context-aware testing agent with safe cleanup for CryptoChecker platform",
            purpose="Execute comprehensive testing with project context awareness",
            tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "mcp__zen__zen_gemini_query"],
            capabilities=capabilities,
            workflows=workflows,
            context_requirements=["README.md", "CLAUDE.md", "test_*.py files"],
            cost_profile={"gemini_flash": "low", "deep_research": "none", "compute": "medium"},
            best_for=[
                "Crypto roulette testing",
                "API endpoint validation", 
                "Authentication flow testing",
                "Balance synchronization tests",
                "Test suite maintenance"
            ],
            avoid_for=[
                "Complex architecture decisions",
                "Major system overhauls",
                "Deep performance analysis"
            ]
        )
    
    def _create_deep_debugging_agent(self) -> CryptoAgent:
        """
        Deep Research Debugging Agent
        
        High-powered debugging for complex CryptoChecker issues:
        - Uses deep-research (costly) only for critical problems
        - Leverages zen_analysis for multi-perspective debugging
        - Focuses on production-critical gaming platform issues
        """
        capabilities = [
            AgentCapability(
                name="deep_research_analysis",
                description="Comprehensive research for complex debugging",
                tools=["mcp__deep-research__deep_research"],
                cost_level="high",
                use_cases=["Complex system failures", "Unknown error patterns", "Architecture issues"]
            ),
            AgentCapability(
                name="zen_multi_analysis",
                description="Multi-model analysis using zen tools",
                tools=["mcp__zen__zen_analysis", "mcp__zen__zen_gemini_query"],
                cost_level="medium",
                use_cases=["Root cause analysis", "Performance issues", "Security concerns"]
            ),
            AgentCapability(
                name="production_debugging",
                description="Focus on production-critical issues",
                tools=["Read", "Grep", "Bash", "Glob"],
                cost_level="low",
                use_cases=["Gaming system failures", "API errors", "Database issues"]
            )
        ]
        
        workflows = [
            AgentWorkflow(
                name="critical_issue_debugging",
                steps=[
                    {"action": "gather_context", "tools": ["Read", "Grep"], "target": "error logs, system state"},
                    {"action": "deep_research", "tools": ["mcp__deep-research__deep_research"], "target": "complex issue analysis"},
                    {"action": "zen_analysis", "tools": ["mcp__zen__zen_analysis"], "target": "multi-perspective debugging"},
                    {"action": "validate_solution", "tools": ["Bash", "Read"], "target": "test proposed fixes"}
                ],
                conditions={"severity": "critical", "cost_approved": True}
            ),
            AgentWorkflow(
                name="standard_debugging",
                steps=[
                    {"action": "analyze_issue", "tools": ["Read", "Grep"], "target": "identify problem scope"},
                    {"action": "zen_analysis", "tools": ["mcp__zen__zen_analysis"], "target": "focused analysis"},
                    {"action": "test_solution", "tools": ["Bash"], "target": "validate fixes"}
                ],
                conditions={"severity": "moderate", "cost_approved": False}
            )
        ]
        
        return CryptoAgent(
            name="CryptoChecker Deep Research Debugger",
            type=AgentType.DEEP_DEBUGGER,
            description="Advanced debugging with deep research for complex CryptoChecker issues",
            purpose="Solve production-critical problems using comprehensive analysis",
            tools=["mcp__deep-research__deep_research", "mcp__zen__zen_analysis", "mcp__zen__zen_gemini_query", "Read", "Grep", "Bash", "Glob"],
            capabilities=capabilities,
            workflows=workflows,
            context_requirements=["Error logs", "System state", "Recent changes"],
            cost_profile={"deep_research": "high", "zen_tools": "medium", "gemini_flash": "low"},
            best_for=[
                "Complex roulette system failures",
                "Authentication system issues",
                "Database synchronization problems",
                "Performance bottlenecks",
                "Security vulnerabilities"
            ],
            avoid_for=[
                "Simple syntax errors",
                "Basic configuration issues", 
                "Minor UI adjustments"
            ]
        )
    
    def _create_construction_agent(self) -> CryptoAgent:
        """
        Construction & Overhaul Agent
        
        Major development projects using zen tools orchestration:
        - Planner → Analysis → Code Review → Consensus → Debug for major projects
        - Consensus → ThinkDeep → Debug for minor fixes
        """
        capabilities = [
            AgentCapability(
                name="zen_orchestration_major",
                description="Full zen workflow for major projects",
                tools=["mcp__zen__zen_gemini_query"],
                cost_level="high",
                use_cases=["New game systems", "Major API overhauls", "Architecture changes"]
            ),
            AgentCapability(
                name="zen_orchestration_minor", 
                description="Streamlined zen workflow for fixes",
                tools=["mcp__zen__zen_gemini_query"],
                cost_level="medium",
                use_cases=["Bug fixes", "Feature enhancements", "Performance improvements"]
            ),
            AgentCapability(
                name="comprehensive_development",
                description="Full development lifecycle management",
                tools=["Read", "Write", "Edit", "MultiEdit", "Bash"],
                cost_level="medium",
                use_cases=["Code implementation", "Testing", "Documentation"]
            )
        ]
        
        workflows = [
            AgentWorkflow(
                name="major_project_workflow",
                steps=[
                    {"action": "zen_planner", "tools": ["mcp__zen__zen_gemini_query"], "target": "break down complex features"},
                    {"action": "zen_analysis", "tools": ["mcp__zen__zen_analysis"], "target": "comprehensive feature analysis"},
                    {"action": "implement", "tools": ["Write", "Edit", "MultiEdit"], "target": "code implementation"},
                    {"action": "zen_codereview", "tools": ["mcp__zen__zen_gemini_query"], "target": "professional code review"},
                    {"action": "zen_consensus", "tools": ["mcp__zen__zen_gemini_query"], "target": "multi-model validation"},
                    {"action": "zen_debug", "tools": ["mcp__zen__zen_gemini_query"], "target": "issue resolution"}
                ],
                conditions={"complexity": "high", "scope": "major"}
            ),
            AgentWorkflow(
                name="minor_fix_workflow",
                steps=[
                    {"action": "zen_consensus", "tools": ["mcp__zen__zen_gemini_query"], "target": "quick validation"},
                    {"action": "implement", "tools": ["Edit", "Write"], "target": "apply fixes"},
                    {"action": "zen_thinkdeep", "tools": ["mcp__zen__zen_gemini_query"], "target": "focused analysis"},
                    {"action": "zen_debug", "tools": ["mcp__zen__zen_gemini_query"], "target": "targeted debugging"}
                ],
                conditions={"complexity": "low", "scope": "minor"}
            )
        ]
        
        return CryptoAgent(
            name="CryptoChecker Construction & Overhaul Agent",
            type=AgentType.CONSTRUCTOR,
            description="Major development projects with zen tools orchestration",
            purpose="Handle complex development workflows with intelligent tool selection",
            tools=["mcp__zen__zen_gemini_query", "mcp__zen__zen_analysis", "Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob"],
            capabilities=capabilities,
            workflows=workflows,
            context_requirements=["Project architecture", "Existing codebase", "Requirements"],
            cost_profile={"zen_tools": "high", "gemini_flash": "high", "implementation": "medium"},
            best_for=[
                "New gaming features",
                "API system overhauls",
                "Database migrations",
                "Major refactoring",
                "Performance optimization"
            ],
            avoid_for=[
                "Simple bug fixes",
                "Documentation updates",
                "Basic configuration changes"
            ]
        )
    
    def _create_context_agent(self) -> CryptoAgent:
        """
        Context & Documentation Agent
        
        Maintains project knowledge and documentation awareness:
        - Reads and indexes all .md files
        - Maintains awareness of CLAUDE.md instructions
        - Provides context to other agents
        """
        capabilities = [
            AgentCapability(
                name="documentation_indexing",
                description="Read and index all project documentation",
                tools=["Read", "Glob", "Grep"],
                cost_level="low",
                use_cases=["Context gathering", "Documentation analysis", "Knowledge base"]
            ),
            AgentCapability(
                name="context_provision",
                description="Provide context to other agents",
                tools=["Read", "mcp__zen__zen_gemini_query"],
                cost_level="low",
                use_cases=["Agent briefing", "Context sharing", "Knowledge transfer"]
            ),
            AgentCapability(
                name="instruction_awareness",
                description="Maintain awareness of CLAUDE.md instructions",
                tools=["Read", "WebFetch"],
                cost_level="low",
                use_cases=["Instruction compliance", "Guideline enforcement", "Best practices"]
            )
        ]
        
        workflows = [
            AgentWorkflow(
                name="context_update",
                steps=[
                    {"action": "scan_docs", "tools": ["Glob"], "target": "find all .md files"},
                    {"action": "read_content", "tools": ["Read"], "target": "index documentation"},
                    {"action": "analyze_context", "tools": ["mcp__zen__zen_gemini_query"], "target": "extract key information"},
                    {"action": "update_index", "tools": ["Write"], "target": "maintain knowledge base"}
                ],
                conditions={"frequency": "on_demand", "trigger": "documentation_change"}
            )
        ]
        
        return CryptoAgent(
            name="CryptoChecker Context & Documentation Agent", 
            type=AgentType.CONTEXT_KEEPER,
            description="Maintain project knowledge and documentation awareness",
            purpose="Provide context and knowledge management for other agents",
            tools=["Read", "Glob", "Grep", "WebFetch", "mcp__zen__zen_gemini_query", "Write"],
            capabilities=capabilities,
            workflows=workflows,
            context_requirements=["All .md files", "Project structure", "Recent changes"],
            cost_profile={"gemini_flash": "low", "computation": "low", "storage": "low"},
            best_for=[
                "Knowledge management",
                "Context briefings",
                "Documentation analysis",
                "Instruction compliance",
                "Best practice guidance"
            ],
            avoid_for=[
                "Code implementation",
                "Complex debugging",
                "Performance optimization"
            ]
        )
    
    def get_agent(self, agent_type: AgentType) -> CryptoAgent:
        """Get specific agent configuration"""
        return self.agents[agent_type.value]
    
    def recommend_agent(self, task_description: str, complexity: TaskComplexity) -> CryptoAgent:
        """
        Recommend best agent for given task and complexity
        
        Args:
            task_description: Description of the task to be performed
            complexity: Complexity level of the task
            
        Returns:
            Recommended agent configuration
        """
        task_lower = task_description.lower()
        
        # Context and documentation tasks
        if any(word in task_lower for word in ['document', 'readme', 'context', 'instruction']):
            return self.get_agent(AgentType.CONTEXT_KEEPER)
        
        # Testing tasks
        if any(word in task_lower for word in ['test', 'validate', 'verify', 'check', 'qa']):
            return self.get_agent(AgentType.TESTER)
        
        # Complex debugging tasks
        if complexity in [TaskComplexity.CRITICAL, TaskComplexity.COMPLEX] and any(word in task_lower for word in ['debug', 'error', 'bug', 'issue', 'problem', 'fail']):
            return self.get_agent(AgentType.DEEP_DEBUGGER)
        
        # Construction and development tasks
        if any(word in task_lower for word in ['build', 'implement', 'create', 'develop', 'feature', 'overhaul', 'refactor']):
            if complexity in [TaskComplexity.COMPLEX, TaskComplexity.CRITICAL]:
                return self.get_agent(AgentType.CONSTRUCTOR)
            else:
                return self.get_agent(AgentType.TESTER)  # Simple implementations can use tester
        
        # Default to context keeper for unclear tasks
        return self.get_agent(AgentType.CONTEXT_KEEPER)
    
    def get_project_status(self) -> Dict[str, Any]:
        """Get current project status and context"""
        return {
            "platform": "CryptoChecker Gaming Platform",
            "status": "PRODUCTION READY ✅",
            "core_features": {
                "crypto_roulette": "✅ Complete with 40+ test scenarios",
                "authentication": "✅ JWT + session management",
                "virtual_economy": "✅ GEM coins with cross-component sync", 
                "api_ecosystem": "✅ 25+ REST endpoints",
                "testing_suite": "✅ Comprehensive validation"
            },
            "recent_fixes": [
                "Custom bet amount bug resolved",
                "401 Unauthorized errors eliminated", 
                "Professional branding complete",
                "Route conflict resolution"
            ],
            "agents_available": list(self.agents.keys()),
            "recommended_usage": {
                "testing": "crypto-tester for comprehensive testing",
                "debugging": "crypto-deep-debugger for complex issues",
                "development": "crypto-constructor for major features", 
                "context": "crypto-context-keeper for documentation"
            }
        }

# Global instance for easy access
crypto_agents = CryptoCheckerAgentsConfig()

def get_crypto_agent(task: str, complexity: str = "moderate") -> CryptoAgent:
    """
    Convenient function to get recommended agent
    
    Usage:
        agent = get_crypto_agent("run comprehensive tests", "moderate")
        agent = get_crypto_agent("debug roulette system failure", "critical")  
        agent = get_crypto_agent("implement new gaming feature", "complex")
    """
    complexity_map = {
        "simple": TaskComplexity.SIMPLE,
        "moderate": TaskComplexity.MODERATE, 
        "complex": TaskComplexity.COMPLEX,
        "critical": TaskComplexity.CRITICAL
    }
    
    return crypto_agents.recommend_agent(task, complexity_map.get(complexity, TaskComplexity.MODERATE))

if __name__ == "__main__":
    # Demo the agents system
    print("🎰 CryptoChecker Ultimate Agents Configuration")
    print("=" * 60)
    
    status = crypto_agents.get_project_status()
    print(f"\n📊 Platform Status: {status['status']}")
    print(f"🎮 Platform: {status['platform']}")
    
    print(f"\n🤖 Available Agents: {len(crypto_agents.agents)}")
    for agent_name in status['agents_available']:
        agent = crypto_agents.agents[agent_name]
        print(f"  • {agent.name}")
        print(f"    Purpose: {agent.purpose}")
        print(f"    Tools: {len(agent.tools)} available")
        print()
    
    # Example recommendations
    print("💡 Example Agent Recommendations:")
    examples = [
        ("run comprehensive tests on crypto roulette", "moderate"),
        ("debug complex authentication failure", "critical"),
        ("implement new dice game feature", "complex"),
        ("update project documentation", "simple")
    ]
    
    for task, complexity in examples:
        recommended = get_crypto_agent(task, complexity)
        print(f"  Task: {task}")
        print(f"  Complexity: {complexity}")
        print(f"  Recommended: {recommended.name}")
        print()