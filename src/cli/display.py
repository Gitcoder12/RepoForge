"""
RepoForge Engine Display – Professional Dashboard
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.live import Live

console = Console()


class Display:

    @staticmethod
    def header():
        console.print(
            Panel(
                "🔥 RepoForge Engine\n"
                "Autonomous AI Software Engineering Platform",
                expand=False,
                style="bold cyan"
            )
        )

    @staticmethod
    def progress_bars(stages: dict):
        """Show animated progress bars for pipeline stages."""
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            tasks = {}
            for stage in ["Scanner", "Intelligence", "V4 Analysis", "Agent Council", "Consensus", "Execution", "Validation", "Git", "Report"]:
                tasks[stage] = progress.add_task(f"[cyan]{stage}...", total=100)

            # Simulate progress (in real usage, update from actual stages)
            for i in range(1, 101, 5):
                for task in tasks.values():
                    progress.update(task, advance=5)
                time.sleep(0.02)

    @staticmethod
    def multi_repo_table(projects: list):
        """Render a table of multiple repositories with health scores."""
        table = Table(title="📊 Multi‑Repo Dashboard")
        table.add_column("Repository", style="cyan")
        table.add_column("Health", justify="center")
        table.add_column("Issues", justify="center")
        table.add_column("Last Action", style="green")

        for p in projects:
            table.add_row(
                p.get("name", "unknown"),
                f"{p.get('score', 0)}/100 {p.get('grade', 'N/A')}",
                str(p.get('issues', 0)),
                p.get('last_action', 'none')
            )
        console.print(table)

    @staticmethod
    def forge_result(result, show_progress=True):
        """Main display for a single repo run."""
        Display.header()

        # Optional progress bar
        if show_progress:
            stages = result.get("stages", {})
            Display.progress_bars(stages)

        console.print("\n🎯 Task")
        console.print(result.get("prompt", ""))

        stages = result.get("stages", {})

        # Repository Analysis
        scan = stages.get("scan", {})
        table = Table(title="🔍 Repository Analysis")
        table.add_column("Metric")
        table.add_column("Value")
        stats = scan.get("statistics", {})
        table.add_row("Files", str(stats.get("files", 0)))
        table.add_row("Lines", str(stats.get("lines", 0)))
        languages = scan.get("languages", {})
        if isinstance(languages, dict):
            language_text = ", ".join(languages.keys())
        else:
            language_text = str(languages)
        table.add_row("Languages", language_text)
        console.print(table)

        # Intelligence
        intelligence = stages.get("intelligence", {})
        quality = intelligence.get("quality_score", {})
        console.print("\n🧠 Intelligence")
        if isinstance(quality, dict):
            console.print(f"Quality Score: {quality.get('score', 0)}/100")
            console.print(f"Grade: {quality.get('grade', 'N/A')}")
            breakdown = quality.get("breakdown", {})
            if breakdown:
                console.print("\nBreakdown:")
                for key, value in breakdown.items():
                    console.print(f"  {key.title()}: {value}%")
        else:
            console.print(f"Quality Score: {quality}/100")

        # V4 Improvement Intelligence
        v4 = stages.get("v4_analysis", {})
        if v4:
            console.print("\n🧠 V4 Improvement Intelligence")
            raw_issues = v4.get("raw_issues", [])
            ranked = v4.get("ranked_issues", [])
            selected = v4.get("selected_improvement")
            console.print(f"   Issues Detected: {len(raw_issues)}")
            if ranked:
                console.print("   Top Improvements:")
                for i, issue in enumerate(ranked[:3], 1):
                    console.print(f"     {i}. {issue.get('type')} (score: {issue.get('value_score', 0):.3f})")
            if selected:
                console.print(f"   ✅ Selected: {selected.get('type')}")
            else:
                console.print("   ℹ️  No improvement selected")

        # V5 Agent Intelligence
        v5 = stages.get("v5_agents", {})
        if v5 and v5.get("enabled", False):
            console.print("\n🧠 Agent Council")
            coordinated = v5.get("coordinated", {})
            if coordinated:
                agents = coordinated.get("agents_run", [])
                if agents:
                    console.print(f"   Agents: {', '.join(agents)}")
                suggestions_count = len(coordinated.get("findings", []))
                console.print(f"   Suggestions: {suggestions_count}")

            consensus = v5.get("consensus", {})
            selected_actions = consensus.get("selected_actions", [])
            if selected_actions:
                console.print("\n   🎯 Selected Action:")
                top = selected_actions[0]
                console.print(f"      {top['action']}")
                console.print(f"      Priority: {top['priority']}/3")
                console.print(f"      Score: {top['score']:.2f}")
                console.print(f"      Agent: {', '.join(top['agent'])}")
            else:
                console.print("   ℹ️  No action selected by consensus.")

        # Recommendations
        recommendations = intelligence.get("recommendations", [])
        if recommendations:
            console.print("\n💡 Recommendations")
            for item in recommendations[:5]:
                if isinstance(item, dict):
                    console.print(f"- {item.get('title', '')}")
                else:
                    console.print(f"- {item}")

        # Forge Actions
        forge = stages.get("forge", {})
        console.print("\n🔨 Forge Actions")
        forge_table = Table()
        forge_table.add_column("Metric")
        forge_table.add_column("Value")
        if isinstance(forge, dict):
            total = forge.get("total_actions", forge.get("detected", 0))
            completed = forge.get("completed", 0)
        else:
            total = 0
            completed = 0
        forge_table.add_row("Detected", str(total))
        forge_table.add_row("Completed", str(completed))
        console.print(forge_table)

        # Validation
        validation = stages.get("validation", {})
        syntax = validation.get("syntax", {})
        console.print("\n🛡 Safety")
        console.print(f"Validation: {'✅' if syntax.get('passed', False) else '❌'}")

        # Git
        git = stages.get("git", {})
        console.print("\n📦 Git")
        if isinstance(git, dict):
            console.print(git.get("message", "Checkpoint complete"))
        else:
            console.print("Checkpoint complete")

        console.print("\n🚀 RepoForge Engine finished")