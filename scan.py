from pathlib import Path
import shutil
import subprocess
import tempfile

import typer

from repoforge.forge import RepoScanner


def clone_repository(url: str) -> Path:
    """
    Clone GitHub repository temporarily.
    """

    if shutil.which("git") is None:
        typer.echo("❌ Git is not installed.")
        raise typer.Exit()

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="repoforge_"
        )
    )

    typer.echo(
        f"⬇️ Cloning {url}"
    )

    result = subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            url,
            str(temp_dir),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        typer.echo(
            result.stderr
        )

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

        raise typer.Exit()

    return temp_dir



def display_result(result: dict):
    """
    Display scanner output.
    """

    typer.echo("")
    typer.echo(
        "=" * 60
    )

    typer.echo(
        "🚀 RepoForge Analysis"
    )

    typer.echo(
        "=" * 60
    )

    for key, value in result.items():

        typer.echo(
            f"\n{key}:"
        )

        typer.echo(
            str(value)
        )



def run_scan(path: str = "."):
    """
    Run repository scan.
    """

    cleanup = False
    target = None


    # GitHub URL

    if path.startswith(
        (
            "http://",
            "https://"
        )
    ):

        if "github.com" not in path:
            typer.echo(
                "❌ Only GitHub repositories supported."
            )
            raise typer.Exit()


        target = clone_repository(path)
        cleanup = True


    else:

        target = (
            Path(path)
            .expanduser()
            .resolve()
        )


    if not target.exists():

        typer.echo(
            f"❌ Path not found: {target}"
        )

        raise typer.Exit()


    if not target.is_dir():

        typer.echo(
            "❌ Repository must be a directory."
        )

        raise typer.Exit()



    try:

        scanner = RepoScanner(
            target
        )

        result = scanner.analyze()

        display_result(
            result
        )


    finally:

        if cleanup:

            shutil.rmtree(
                target,
                ignore_errors=True,
            )