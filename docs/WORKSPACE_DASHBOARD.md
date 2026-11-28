# RepoForge Workspace Dashboard

## Start

From a RepoForge checkout:

~~~powershell
python -m pip install -e ".[ui]"
streamlit run dashboard.py
~~~

Open the local Streamlit address printed by the command in your browser.

## Find a repository

1. Enter a parent directory such as `C:\Users\you\Projects` or `~/Projects`.
2. Press **Find repositories**.
3. Search by repository name or full path.
4. Select the repository from the sidebar.

Discovery checks for Git working-tree metadata. It does not clone projects, follow symlinks, or enter common dependency/build directories. The scan is bounded to four nested directory levels and 300 repositories by default.

## Repository actions

The Repository Workspace tab offers:
- Overview: Blacksmith repository health and safe repair preview.
- Upgrade options: UpgradeForge's evidence-backed improvement catalogue.
- Discover tests: commands inferred by TestForge; nothing is executed.
- Static validation: Python AST and conservative static checks; no tests are run.

## Agent workbench

Search the specialist role catalogue and choose Architect, Testing, Security, Documentation, Performance, Dependencies, Quality, CI/CD, or Code Review.

Without local Ollama enabled, the workflow performs RepoForge's read-only inspection and planning step. To request a model-generated patch proposal, explicitly enable the local Ollama option and choose an installed model name. It does not contact hosted model APIs. Ollama must already be running locally.

The proposal is displayed for review only. The dashboard does not apply model-generated patches, execute repository tests, or commit changes.

## Megazords

Select two or more discovered repositories to compare complementary capabilities. The score is a heuristic recommendation, not an integration compatibility percentage. Review package versions, API/data contracts, licences, and operational ownership before building an integration.

## Safety boundaries

- No target project tests or build scripts are run.
- No repository-defined hooks or plugins are loaded.
- Workspace discovery is read-only and does not clone or edit repositories.
- Blacksmith repair plans are previews in the dashboard; no automatic file creation is performed here.
- Local Ollama calls may read selected repository context into your local model process; no hosted provider is used by this option.
- RepoForge's existing CLI remains available for exact-path approval and other workflows.

This dashboard is a local developer interface over existing RepoForge services, not a remote hosting service or a sandbox for untrusted code.
