"""
RepoForge Action Parser
Strictly extracts and validates JSON actions.
"""

import json
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("RepoForge.ActionParser")

class ActionParser:
    def parse(self, response: str) -> List[Dict[str, Any]]:
        actions = []
        for block in self.extract_json(response):
            data = self.safe_json_load(block)
            if data is None:
                continue

            if isinstance(data, list):
                for item in data:
                    if self.validate_action(item):
                        actions.append(item)
            elif isinstance(data, dict):
                if self.validate_action(data):
                    actions.append(data)

        # Deduplicate
        unique_actions = []
        seen = set()
        for action in actions:
            key = (action.get("type"), action.get("file"), action.get("content"))
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)

        return unique_actions

    def safe_json_load(self, text: str):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                # Repair multiline strings in JSON
                fixed = re.sub(
                    r'("content"\s*:\s*")(.*?)(")',
                    lambda match: match.group(1) + match.group(2).replace("\n", "\\n") + match.group(3),
                    text,
                    flags=re.DOTALL
                )
                return json.loads(fixed)
            except Exception as e:
                logger.error(f"JSON repair failed: {e}")
                return None

    def extract_json(self, text: str) -> List[str]:
        if not isinstance(text, str):
            return []
        blocks = []
        # Markdown JSON blocks
        matches = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
        blocks.extend(matches)

        # Raw JSON
        for start_char, end_char in [("[", "]"), ("{", "}")]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1:
                blocks.append(text[start:end + 1])

        return list(set(block.strip() for block in blocks if block.strip()))

    def validate_action(self, action: Dict[str, Any]) -> bool:
        if not isinstance(action, dict):
            return False
        if not all(key in action for key in ["type", "file", "content"]):
            return False
        if action["type"] not in ["create", "modify", "delete"]:
            return False
        if not isinstance(action["file"], str) or not isinstance(action["content"], str):
            return False
        
        # Security check
        unsafe = ["..", "~", "/etc", "C:\\"]
        if any(item in action["file"] for item in unsafe):
            logger.warning(f"Blocked unsafe path: {action['file']}")
            return False

        return True
