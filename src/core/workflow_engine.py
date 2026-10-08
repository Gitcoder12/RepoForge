"""
RepoForge Workflow Engine V3 + V4 Decision Layer + V5 Phase 3 (Coordinator + Consensus)

Pipeline:

Scanner
   ↓
Intelligence Engine
   ↓
[V4 Issue Detector → Priority Engine → Improvement Selector]
   ↓
[V5 Agent Coordinator → Consensus Engine → Auto‑Select Best Action]
   ↓
Difficulty Engine
   ↓
AI Strategist (receives selected action)
   ↓
AI Orchestrator
   ↓
Action Runner
   ↓
Validator
   ↓
Git Checkpoint
   ↓
Reporter
"""

import os
from typing import Dict, Any

from repoforge.validator import RepoValidator
from repoforge.git_manager import GitManager
from repoforge.orchestrator import AIOrchestrator
from repoforge.router import AIRouter
from repoforge.action_runner import ActionRunner
from repoforge.action_parser import ActionParser
from repoforge.scanner import RepoScanner
from repoforge.strategist import AIStrategist
from repoforge.reporter import Reporter

from repoforge.intelligence.intelligence_engine import IntelligenceEngine


class WorkflowEngine:

    def __init__(
        self,
        repo_path: str,
    ):

        self.repo_path = repo_path

        self.scanner = RepoScanner(
            repo_path
        )

        self.intelligence = IntelligenceEngine(
            repo_path
        )

        self.strategist = AIStrategist()

        self.ai = AIOrchestrator()

        self.runner = ActionRunner(
            repo_path
        )

        self.validator = RepoValidator(
            repo_path
        )

        self.git = GitManager(
            repo_path
        )

        self.reporter = Reporter(
            repo_path
        )



    def normalize_scan(
        self,
        scan
    ):
        # Accept ScanResult dataclass or dict
        if hasattr(scan, "to_dict"):
            scan = scan.to_dict()

        if not isinstance(scan, dict):
            return {
                "statistics": {"files": 0, "lines": 0, "total_files": 0},
                "languages": {},
                "metadata": {},
                "profile": {},
            }

        # Normalize key names used by the rest of the pipeline
        stats = scan.get("statistics", {})
        if "files" not in stats and "total_files" in stats:
            stats["files"] = stats["total_files"]
        if "lines" not in stats and "total_lines" in stats:
            stats["lines"] = stats["total_lines"]
        scan["statistics"] = stats
        return scan



    def normalize_intelligence(
        self,
        intelligence
    ):

        if not isinstance(
            intelligence,
            dict
        ):

            intelligence = {}

        if "quality_score" not in intelligence:

            quality = intelligence.get(
                "quality",
                {}
            )

            score = intelligence.get(
                "score",
                {}
            )

            intelligence["quality_score"] = {

                "score":

                    score.get(
                        "score",
                        quality.get(
                            "score",
                            0
                        )
                    ),

                "grade":

                    score.get(
                        "grade",
                        quality.get(
                            "grade",
                            "N/A"
                        )
                    )

            }

        return intelligence



    def calculate_difficulty(
        self,
        scan
    ):

        stats = scan.get(
            "statistics",
            {}
        )

        files = stats.get(
            "files",
            0
        )

        lines = stats.get(
            "lines",
            0
        )

        if files > 2000 or lines > 300000:

            return {

                "level": "Extreme",

                "reason":
                    "Large enterprise repository"

            }

        if files > 500 or lines > 100000:

            return {

                "level": "Hard",

                "reason":
                    "Large repository"

            }

        return {

            "level": "Normal",

            "reason":
                "Standard repository"

        }



    def execute(
        self,
        prompt: str,
        dry_run: bool = False,
        fix_mode: bool = False,
    ) -> Dict[str, Any]:

        result = {

            "prompt": prompt,

            "stages": {}

        }

        # ============================================================
        # Scanner
        # ============================================================

        scan = self.normalize_scan(

            self.scanner.scan()

        )

        result["stages"]["scan"] = scan

        # ============================================================
        # Smart Model Routing (best provider for this repo + task)
        # ============================================================
        import os
        router = AIRouter()
        provider, reason = router.select(prompt=prompt, scan=scan)
        os.environ["REPOFORGE_PROVIDER"] = provider
        result["stages"]["routing"] = {
            "provider": provider,
            "reason": reason,
        }
        print(f"  🎯 Model routing: {provider}  ({reason})")

        # ============================================================
        # Intelligence
        # ============================================================

        intelligence = self.normalize_intelligence(

            self.intelligence.analyze(
                scan
            )

        )

        result["stages"]["intelligence"] = intelligence

        # ============================================================
        # V4 DECISION LAYER
        # ============================================================

        from repoforge.issue_detector import IssueDetector
        from repoforge.priority_engine import PriorityEngine
        from repoforge.improvement_selector import ImprovementSelector

        detector = IssueDetector()
        raw_issues = detector.detect(scan, intelligence)

        priority = PriorityEngine()
        ranked_issues = priority.rank(raw_issues)

        selector = ImprovementSelector()
        selected_improvement = selector.select(ranked_issues)

        # Build multi-issue plan for engineering mode
        plan_issues = selector.select_many(ranked_issues, limit=5) if hasattr(selector, "select_many") else (
            [selected_improvement] if selected_improvement else []
        )
        if selected_improvement and selected_improvement not in plan_issues:
            plan_issues = [selected_improvement] + [i for i in plan_issues if i is not selected_improvement]

        result["stages"]["v4_analysis"] = {
            "raw_issues": raw_issues,
            "ranked_issues": ranked_issues,
            "selected_improvement": selected_improvement,
            "plan_issues": plan_issues,
            "fix_mode": fix_mode,
        }

        if plan_issues:
            print(f"  📋 Audit plan: {len(plan_issues)} prioritized issue(s) to address")
            for idx, iss in enumerate(plan_issues[:5], 1):
                print(f"     {idx}. [{iss.get('type')}] {str(iss.get('description', ''))[:70]}")


        # ============================================================
        # V5 AGENT COORDINATOR + CONSENSUS + AUTO-SELECT
        # ============================================================

        ENABLE_AGENTS = os.getenv("REPOFORGE_AGENTS", "false").lower() == "true"

        if ENABLE_AGENTS:

            from repoforge.agents.coordinator import AgentCoordinator
            from repoforge.agents.consensus import ConsensusEngine
            from repoforge.agents import (
                ArchitectAgent,
                SecurityAgent,
                TestingAgent,
                PerformanceAgent,
                ReviewAgent,
                DocumentationAgent,
                DependencyAgent
            )

            # Build agent context
            agent_context = {
                "selected_improvement": selected_improvement,
                "scan": scan,
                "intelligence": intelligence,
                "difficulty": self.calculate_difficulty(scan)  # computed below, but can be pre-calculated
            }

            # 1. Coordinator
            coordinator = AgentCoordinator()
            coordinator.register_all([
                ArchitectAgent(),
                SecurityAgent(),
                TestingAgent(),
                PerformanceAgent(),
                ReviewAgent(),
                DocumentationAgent(),
                DependencyAgent(),
            ])
            coordinated = coordinator.run(agent_context)

            # 2. Consensus
            consensus = ConsensusEngine()
            consensus_result = consensus.process(coordinated)

            # 3. Select best action and pass to AI
            selected_actions = consensus_result.get("selected_actions", [])
            if selected_actions:
                best_action = selected_actions[0]
                # Format as a dict compatible with the existing improvement structure
                selected_improvement = {
                    "type": "consensus_action",
                    "description": best_action["action"],
                    "agent": best_action["agent"],
                    "priority": best_action["priority"],
                    "score": best_action["score"],
                    "rationale": f"Selected by consensus from agents: {', '.join(best_action['agent'])}",
                }
                enhanced_plan = {
                    "original_improvement": None,  # V4 may have had one, but we override
                    "consensus_actions": selected_actions,
                    "all_suggestions": coordinated.get("findings", []),
                    "summary": f"Consensus selected '{best_action['action']}' as top action."
                }
            else:
                # No consensus actions – keep original (or None)
                selected_improvement = selected_improvement  # unchanged
                enhanced_plan = {
                    "original_improvement": selected_improvement,
                    "consensus_actions": [],
                    "all_suggestions": coordinated.get("findings", []),
                    "summary": "No consensus actions; using original improvement."
                }

            result["stages"]["v5_agents"] = {
                "enabled": True,
                "coordinated": coordinated,
                "consensus": consensus_result,
                "enhanced_plan": enhanced_plan,
                "selected_improvement": selected_improvement,
            }

        else:

            result["stages"]["v5_agents"] = {
                "enabled": False,
                "reason": "Agents disabled. Set REPOFORGE_AGENTS=true to enable."
            }

        # ============================================================
        # FIX: expose quality score globally
        # ============================================================

        result["quality_score"] = intelligence.get(

            "quality_score",

            {
                "score": 0,
                "grade": "N/A"
            }

        )

        # ============================================================
        # Difficulty
        # ============================================================

        difficulty = self.calculate_difficulty(
            scan
        )

        result["stages"]["difficulty"] = difficulty

        # ============================================================
        # Strategy
        # ============================================================

        plan = self.strategist.create_plan(

            prompt,

            context={

                "issues":
                    scan.get(
                        "issues",
                        []
                    ),

                "security":
                    scan.get(
                        "security",
                        []
                    )

            },

            difficulty=difficulty

        )

        result["stages"]["strategy"] = {

            "mode":
                plan.mode,

            "roles":
                plan.roles,

            "discussion_rounds":
                plan.discussion_rounds,

            "review":
                plan.review,

            "parallel":
                plan.parallel

        }

        # ============================================================
        # AI Orchestrator — Audit plan drives engineering actions
        # ============================================================

        # Enrich prompt with prioritized audit issues (diagnosis → hands)
        plan_issues = result["stages"].get("v4_analysis", {}).get("plan_issues") or []
        if plan_issues or fix_mode:
            issue_lines = []
            for idx, iss in enumerate(plan_issues[:5], 1):
                issue_lines.append(
                    f"{idx}. [{iss.get('type')}] {iss.get('description')} "
                    f"| Fix: {iss.get('recommendation')} "
                    f"| Location: {iss.get('location') or 'repo root'}"
                )
            issues_block = "\n".join(issue_lines) if issue_lines else "No ranked issues; improve based on user task only."
            engineering_prompt = f"""{prompt}

REPOFORGE AUDIT PLAN (fix these with small, safe file changes):
{issues_block}

Rules:
- Prefer creating missing tests/, .github/workflows/ci.yml, LICENSE, or improving README sections.
- Output ONLY a JSON array of actions: [{{"type":"create"|"modify","file":"relative/path","content":"...","reason":"..."}}]
- Keep changes minimal and high-value. Do not rewrite unrelated files.
"""
        else:
            engineering_prompt = prompt

        ai_result = self.ai.execute(
            engineering_prompt,
            context={
                "scan": scan,
                "intelligence": intelligence,
                "difficulty": difficulty,
                "strategy": result["stages"]["strategy"],
                "selected_improvement": selected_improvement,
                "plan_issues": plan_issues,
                "fix_mode": fix_mode,
            },
        )

        result["stages"]["ai"] = ai_result

        # ============================================================
        # Parse AI response
        # ============================================================

        if isinstance(
            ai_result,
            dict
        ):

            response = ai_result.get(
                "response",
                ""
            )

        else:

            response = str(
                ai_result
            )

        # ============================================================
        # Forge (Action Runner)
        # ============================================================

        parser = ActionParser()
        actions = parser.parse(response) if response else []
        # Also accept if AI already returned a list of action dicts
        if isinstance(ai_result, dict) and isinstance(ai_result.get("actions"), list):
            actions = ai_result["actions"] or actions

        action_result = self.runner.run(actions, dry_run=dry_run)

        result["stages"]["forge"] = action_result

        # ============================================================
        # Validation
        # ============================================================

        validation = self.validator.validate()

        result["stages"]["validation"] = validation

        # ============================================================
        # Git Checkpoint
        # ============================================================

        completed_actions = 0

        if isinstance(
            action_result,
            dict
        ):

            completed_actions = action_result.get(
                "completed",
                0
            )

        syntax_ok = (

            validation.get(
                "syntax",
                {}
            ).get(
                "passed",
                False
            )

        )

        # Always create a Git checkpoint when we actually changed something.
        # Validation is advisory – strict failures no longer block the product promise.
        if completed_actions > 0:
            try:
                git_result = self.git.save_state("RepoForge AI improvement")
                if not isinstance(git_result, dict):
                    git_result = {"success": True, "message": str(git_result)}
                if not syntax_ok:
                    git_result["warning"] = "Validation had warnings (checkpoint still created)"
            except Exception as e:
                git_result = {"success": False, "message": f"Git checkpoint failed: {e}"}
        elif completed_actions == 0:
            git_result = {
                "success": False,
                "message": "No Forge actions completed. Git checkpoint skipped.",
            }
        else:
            git_result = {
                "success": False,
                "message": "Nothing to checkpoint.",
            }

        result["stages"]["git"] = git_result

        # ============================================================
        # Reporter
        # ============================================================

        result["stages"]["report"] = self.reporter.generate(
            result
        )

        return result