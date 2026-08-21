#!/usr/bin/env python3
"""
RepoForge Batch Runner
Scans multiple repositories from a config file in parallel.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .runner import RepoForgeRunner


class BatchRunner:
    def __init__(self, config_path: str, output_dir: str = "reports_batch"):
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        self.repos = self._load_config()
    
    def _load_config(self) -> List[str]:
        """Load repo paths from JSON or YAML config."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        data = json.loads(self.config_path.read_text(encoding='utf-8-sig'))
        
        # Support both {"repos": [...]} and just [...]
        if isinstance(data, list):
            return data
        return data.get("repos", [])
    
    def run(self) -> Dict[str, Any]:
        """Run scans in parallel."""
        results = {}
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 Scanning {len(self.repos)} repos...")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for repo in self.repos:
                out_subdir = self.output_dir / Path(repo).name
                futures[executor.submit(self._scan_one, repo, out_subdir)] = repo
            
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    result = future.result()
                    results[repo] = result
                    print(f"✅ {Path(repo).name}")
                except Exception as e:
                    results[repo] = {"error": str(e)}
                    print(f"❌ {Path(repo).name}: {e}")
        
        # Write aggregate summary
        summary_path = self.output_dir / "batch_summary.json"
        summary_path.write_text(
            json.dumps(results, indent=2, default=str),
            encoding='utf-8'
        )
        
        return results
    
    def _scan_one(self, repo_path: str, out_dir: Path) -> dict:
        runner = RepoForgeRunner(repo_path, str(out_dir))
        return runner.run()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch scan repos")
    parser.add_argument("config", help="JSON file with list of repo paths")
    parser.add_argument("-o", "--output", default="reports_batch")
    args = parser.parse_args()
    
    runner = BatchRunner(args.config, args.output)
    runner.run()


if __name__ == "__main__":
    main()
