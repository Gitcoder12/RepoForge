import argparse
import asyncio
import logging
from ..pipeline import RepoForgePipeline

logger = logging.getLogger("RepoForge.CLI")

def app():
    """The main entry point for the RepoForge CLI."""
    parser = argparse.ArgumentParser(description="RepoForge: Multi-Agent AI Orchestrator")
    
    # Required argument
    parser.add_argument("repo_path", help="Path to the repository to improve")
    
    # Optional arguments
    parser.add_argument("-p", "--prompt", default="", help="Optional prompt to guide the agents")
    parser.add_argument("--no-dry-run", action="store_true", help="Actually write files to disk (default is dry run)")
    
    args = parser.parse_args()

    logger.info(f"Initializing RepoForge for {args.repo_path}")
    
    # Instantiate the pipeline
    pipeline = RepoForgePipeline(
        repo_path=args.repo_path,
        dry_run=not args.no_dry_run
    )

    # Run the async pipeline
    try:
        result = asyncio.run(pipeline.run(prompt=args.prompt))
        
        print("\n" + "="*40)
        print(" FORGE COMPLETE")
        print("="*40)
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"Winning Agent: {result['decision']['winning_agent']}")
            print(f"Target File: {result['decision']['target_file']}")
            print(f"Reasoning: {result['decision']['reasoning']}")
            
    except KeyboardInterrupt:
        logger.warning("CLI interrupted by user.")
    except Exception as e:
        logger.critical(f"Pipeline crashed: {e}")
