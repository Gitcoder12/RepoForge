"""Local-first Streamlit workspace for RepoForge.

Run from an editable installation with:
    streamlit run dashboard.py

Repository discovery is metadata-only. No target project is executed or modified.
"""

from __future__ import annotations  # noqa: I001

import os
from pathlib import Path
from typing import Any

from repoforge.blacksmith import Blacksmith
from repoforge.megazord import MegazordEngine
from repoforge.testing import TestForge
from repoforge.upgrades import UpgradePlanner
from repoforge.validator import Validator


IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "dist",
    "build",
    "target",
    "vendor",
    ".next",
    ".nuxt",
}


AGENT_FOCUSES: dict[str, dict[str, str]] = {
    "Architect": {
        "description": "Structure, modules, boundaries, interfaces, and design trade-offs.",
        "request": (
            "Review the repository architecture and propose the highest-value "
            "structural improvements."
        ),
    },
    "Testing": {
        "description": "Test discovery, coverage gaps, edge cases, and regression strategy.",
        "request": (
            "Review testing strategy, discover existing tests, and identify "
            "important behavior-based test gaps."
        ),
    },
    "Security": {
        "description": (
            "Static risk signals, secrets hygiene, permissions, and dependency exposure."
        ),
        "request": (
            "Review security posture and identify evidence-backed risks without "
            "executing repository code."
        ),
    },
    "Documentation": {
        "description": "README accuracy, setup instructions, examples, and developer onboarding.",
        "request": (
            "Review documentation quality and propose specific improvements "
            "grounded in the repository."
        ),
    },
    "Performance": {
        "description": "Potential bottlenecks, complexity hotspots, and measurement strategy.",
        "request": (
            "Review likely performance risks and propose measurable profiling "
            "or optimization steps."
        ),
    },
    "Dependencies": {
        "description": "Manifests, dependency consistency, versions, and supply-chain hygiene.",
        "request": (
            "Review dependency and package configuration; identify consistency "
            "and maintenance risks."
        ),
    },
    "Quality": {
        "description": "Formatting, linting, typing, maintainability, and code quality workflows.",
        "request": "Review code-quality tooling and recommend language-appropriate validation steps.",
    },
    "CI/CD": {
        "description": (
            "Build checks, continuous integration, release workflows, and deployment safety."
        ),
        "request": "Review CI/CD configuration and propose checks based on the actual project stack.",
    },
    "Code Review": {
        "description": "Focused change review, failure modes, correctness, and maintainability.",
        "request": (
            "Perform a cautious engineering review and identify the most consequential "
            "issues with evidence."
        ),
    },
}


def is_git_repository(path: str | Path) -> bool:
    """Return whether a directory is a Git working tree without invoking Git."""
    candidate = Path(path)
    marker = candidate / ".git"
    return candidate.is_dir() and (marker.is_dir() or marker.is_file())


def discover_repositories(
    workspace: str | Path,
    *,
    max_depth: int = 4,
    max_results: int = 300,
) -> list[Path]:
    """Find nested Git working trees without following symlinks or entering vendors."""
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Workspace folder does not exist or is not a directory: {root}")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth must be a non-negative integer")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or max_results < 1:
        raise ValueError("max_results must be a positive integer")

    if is_git_repository(root):
        return [root]

    discovered: list[Path] = []
    for current, directories, _files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        if depth >= max_depth:
            directories[:] = []
        else:
            directories[:] = sorted(
                name
                for name in directories
                if name not in IGNORED_DIRECTORIES and not (current_path / name).is_symlink()
            )

        for name in list(directories):
            candidate = current_path / name
            if is_git_repository(candidate):
                discovered.append(candidate.resolve())
                directories.remove(name)
                if len(discovered) >= max_results:
                    return sorted(
                        discovered,
                        key=lambda item: (item.name.casefold(), str(item).casefold()),
                    )

    return sorted(discovered, key=lambda item: (item.name.casefold(), str(item).casefold()))


def filter_repositories(repositories: list[Path], query: str) -> list[Path]:
    """Filter repository names and full paths case-insensitively."""
    needle = query.strip().casefold()
    if not needle:
        return list(repositories)
    return [
        path
        for path in repositories
        if needle in path.name.casefold() or needle in str(path).casefold()
    ]


def run_local_agent_review(
    repo_path: str | Path,
    focus: str,
    request: str = "",
    *,
    use_local_ollama: bool = False,
    model: str = "llama3",
) -> dict[str, Any]:
    """Run RepoForge's inspect/proposal flow; Ollama is explicit and local-only.

    Without Ollama this returns the read-only inspection and plan. With Ollama,
    it requests a patch proposal but still does not apply any changes.
    """
    from repoforge.forge import ForgeWorkflow

    if focus not in AGENT_FOCUSES:
        raise ValueError(f"Unknown agent focus: {focus}")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model name must not be empty")

    focus_request = AGENT_FOCUSES[focus]["request"]
    full_request = (
        f"{focus_request}\nAdditional request: {request.strip()}"
        if request.strip()
        else focus_request
    )
    return ForgeWorkflow().run(
        repo_path,
        full_request,
        provider="ollama" if use_local_ollama else None,
        model=model.strip() if use_local_ollama else None,
        apply=False,
        run_tests=False,
    )


def render_app() -> None:
    """Render the Streamlit dashboard. Streamlit is an optional dependency."""
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover - exercised by installation, not unit tests
        raise RuntimeError(
            "Install the optional dashboard dependency with "
            "'python -m pip install -e .[ui]' before launching RepoForge."
        ) from exc

    st.set_page_config(page_title="RepoForge Workspace", page_icon="🛠️", layout="wide")
    st.title("RepoForge Workspace")
    st.caption(
        "Find local repositories, inspect engineering health, and route work "
        "through focused agent presets."
    )

    if "repoforge_repositories" not in st.session_state:
        st.session_state.repoforge_repositories = []
    if "repoforge_selected_repo" not in st.session_state:
        st.session_state.repoforge_selected_repo = ""

    with st.sidebar:
        st.header("Workspace")
        default_root = str(Path.home() / "Projects")
        workspace_text = st.text_input(
            "Search location",
            value=st.session_state.get("repoforge_workspace_root", default_root),
            help="Choose a parent folder containing your local Git repositories.",
        )
        st.session_state.repoforge_workspace_root = workspace_text
        if st.button("Find repositories", type="primary", use_container_width=True):
            try:
                found = discover_repositories(workspace_text)
                st.session_state.repoforge_repositories = [str(path) for path in found]
                st.session_state.repoforge_selected_repo = ""
                st.success(f"Found {len(found)} repositories.")
            except (OSError, ValueError) as exc:
                st.error(str(exc))

        all_repositories = [Path(item) for item in st.session_state.repoforge_repositories]
        st.caption(f"{len(all_repositories)} repositories indexed in this session.")
        repo_query = st.text_input("🔎 Search repositories", placeholder="Name or folder path")
        filtered = filter_repositories(all_repositories, repo_query)
        if not filtered:
            st.info("No matching repositories. Scan a workspace folder first.")
            selected_repo = None
        else:
            selected_value = st.selectbox(
                "Open repository",
                options=[str(path) for path in filtered],
                index=(
                    [str(path) for path in filtered].index(st.session_state.repoforge_selected_repo)
                    if st.session_state.repoforge_selected_repo in [str(path) for path in filtered]
                    else 0
                ),
                format_func=lambda value: f"{Path(value).name}  ·  {value}",
            )
            st.session_state.repoforge_selected_repo = selected_value
            selected_repo = Path(selected_value)
        st.divider()
        st.caption(
            "Default mode: local inspection only. No model calls, test execution, or file edits."
        )

    workspace_tab, agents_tab, megazords_tab = st.tabs(
        ["Repository workspace", "Agent workbench", "Megazords"]
    )

    with workspace_tab:
        if selected_repo is None:
            st.info(
                "Choose a workspace folder in the sidebar and search for a repository to begin."
            )
        else:
            st.subheader(selected_repo.name)
            st.caption(str(selected_repo))
            mode = st.radio(
                "Choose an action",
                ["Overview", "Upgrade options", "Discover tests", "Static validation"],
                horizontal=True,
            )
            if st.button("Run selected check", type="primary", key="repoforge_run_check"):
                try:
                    if mode == "Overview":
                        snapshot = Blacksmith(selected_repo).inspect()
                        st.session_state.repoforge_action_report = {
                            "action": mode,
                            "inspection": snapshot,
                            "safe_repair_preview": Blacksmith(selected_repo).repair_plan(snapshot),
                        }
                    elif mode == "Upgrade options":
                        snapshot = Blacksmith(selected_repo).inspect()
                        st.session_state.repoforge_action_report = UpgradePlanner().build(snapshot)
                    elif mode == "Discover tests":
                        st.session_state.repoforge_action_report = TestForge(selected_repo).plan()
                    else:
                        import asyncio

                        st.session_state.repoforge_action_report = asyncio.run(
                            Validator(str(selected_repo)).validate(run_tests=False)
                        )
                except Exception as exc:  # report errors without interrupting the workspace
                    st.session_state.repoforge_action_report = {
                        "status": "error",
                        "message": str(exc),
                    }

            report = st.session_state.get("repoforge_action_report")
            if report:
                if report.get("action") == "Overview":
                    inspection = report["inspection"]
                    dimensions = inspection["rank"]["dimensions"]
                    metrics = st.columns(4)
                    metrics[0].metric("RepoRank", f"{inspection['rank']['score']}/100")
                    metrics[1].metric("Files scanned", inspection["files_scanned"])
                    metrics[2].metric("Languages", len(inspection["languages"]))
                    metrics[3].metric("Capabilities", len(inspection["capabilities"]))
                    st.write("**Language inventory**")
                    st.json(inspection["languages"])
                    st.write("**Hygiene dimensions**")
                    st.json(dimensions)
                    st.write("**Repair preview — no files changed**")
                    st.json(report["safe_repair_preview"])
                else:
                    st.json(report)
            else:
                st.write(
                    "Select an action above. Checks are read-only and do not "
                    "execute the target project's tests."
                )

    with agents_tab:
        st.subheader("Agent workbench")
        st.caption(
            "Search a specialist role, select a focus, and request a read-only "
            "plan or a local Ollama proposal."
        )
        agent_query = st.text_input(
            "🔎 Search agents", placeholder="Architecture, testing, security…"
        )
        matching_agents = [
            name
            for name, item in AGENT_FOCUSES.items()
            if agent_query.casefold() in name.casefold()
            or agent_query.casefold() in item["description"].casefold()
        ]
        if not matching_agents:
            st.warning("No matching agent roles.")
        else:
            focus = st.selectbox("Specialist focus", matching_agents)
            st.write(AGENT_FOCUSES[focus]["description"])
            additional_request = st.text_area(
                "What should this agent focus on?",
                placeholder="Example: Check API boundaries and missing regression tests.",
                height=90,
            )
            use_ollama = st.checkbox(
                "Use a local Ollama model to draft a patch proposal",
                value=False,
                help="No hosted API is called. Ollama must already be running on your computer.",
            )
            model = st.text_input("Local Ollama model", value="llama3", disabled=not use_ollama)
            if selected_repo is None:
                st.info("Choose a repository in the sidebar first.")
            elif st.button("Run agent workflow", type="primary", disabled=selected_repo is None):
                try:
                    with st.spinner("Inspecting repository…"):
                        result = run_local_agent_review(
                            selected_repo,
                            focus,
                            additional_request,
                            use_local_ollama=use_ollama,
                            model=model,
                        )
                    st.session_state.repoforge_agent_report = result
                except Exception as exc:
                    st.session_state.repoforge_agent_report = {
                        "status": "error",
                        "message": str(exc),
                    }

            agent_report = st.session_state.get("repoforge_agent_report")
            if agent_report:
                st.write(f"**Workflow status:** {agent_report.get('status', 'unknown')}")
                if use_ollama:
                    st.caption("Model output is a proposal only. No changes are applied.")
                elif agent_report.get("status") == "plan_only":
                    st.caption(
                        "Read-only inspection completed. Enable local Ollama to "
                        "request a model-generated patch proposal."
                    )
                st.json(agent_report)

    with megazords_tab:
        st.subheader("Repository combinations")
        st.caption(
            "Compare two or more discovered repositories. Fit scores are "
            "heuristic hypotheses, not compatibility guarantees."
        )
        if len(all_repositories) < 2:
            st.info("Scan a workspace containing at least two Git repositories.")
        else:
            selected_paths = st.multiselect(
                "Choose repositories to compare",
                options=[str(path) for path in all_repositories],
                format_func=lambda value: f"{Path(value).name}  ·  {value}",
            )
            top_k = st.slider("Suggestions", min_value=1, max_value=30, value=10)
            if st.button(
                "Find complementary projects",
                type="primary",
                disabled=len(selected_paths) < 2,
            ):
                try:
                    result = MegazordEngine().suggest(selected_paths, top_k=top_k)
                    st.session_state.repoforge_megazord_report = result
                except Exception as exc:
                    st.session_state.repoforge_megazord_report = {
                        "status": "error",
                        "message": str(exc),
                    }
            megazord_report = st.session_state.get("repoforge_megazord_report")
            if megazord_report:
                st.metric("Pairings evaluated", megazord_report.get("pairings_evaluated", 0))
                st.json(megazord_report)


def main() -> None:
    """Streamlit-compatible entry point for console runners."""
    render_app()
