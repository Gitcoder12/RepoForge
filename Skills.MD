# REPOFORGE SKILLS.MD - Agent Tool Definitions

##  OVERVIEW
This document defines the executable skills (tools) available to the autonomous agents operating within RepoForge. Any LLM (OpenAI, Anthropic, Grok, Local) must strictly adhere to these JSON schemas when invoking a tool.

##  1. FILE SYSTEM SKILLS

### `read_file`
Reads the contents of a file.
- **Parameters:** 
  - `path` (string): The relative path to the file.
- **Returns:** `string` (The file contents)

### `write_file`
Writes or overwrites a file. (Requires Human-in-the-Loop approval if `AGENTS.md` rules are violated).
- **Parameters:**
  - `path` (string): The relative path to the file.
  - `content` (string): The code or text to write.
- **Returns:** `boolean` (Success status)

### `list_directory`
Lists all files in a given directory.
- **Parameters:**
  - `path` (string): The directory path.
- **Returns:** `array` of strings (File names)

---

##  2. CODE EXECUTION & VALIDATION SKILLS

### `run_pytest`
Executes the test suite to validate code changes.
- **Parameters:**
  - `target_dir` (string): The directory containing tests (e.g., `./tests`).
- **Returns:** `object` (Test results, pass/fail counts, traceback on failure)

### `lint_code`
Runs `flake8` or `pylint` to enforce PEP 8 standards.
- **Parameters:**
  - `file_path` (string): The file to lint.
- **Returns:** `array` of strings (Linting errors)

### `execute_shell`
Executes a safe shell command (e.g., `pip install`, `npm run build`).
- **Parameters:**
  - `command` (string): The command to run.
- **Returns:** `string` (Terminal output)

---

##  3. VERSION CONTROL SKILLS

### `git_diff`
Shows the changes made to the working directory.
- **Parameters:** None
- **Returns:** `string` (The diff output)

### `git_commit`
Commits the changes with a Conventional Commit message.
- **Parameters:**
  - `message` (string): Must start with `feat:`, `fix:`, or `refactor:`.
- **Returns:** `boolean` (Success status)

---

##  4. EXTERNAL KNOWLEDGE SKILLS

### `web_search`
Searches the web for documentation or solutions.
- **Parameters:**
  - `query` (string): The search query.
- **Returns:** `array` of objects (Title, URL, Snippet)

### `fetch_url`
Scrapes the text content of a documentation page.
- **Parameters:**
  - `url` (string): The URL to fetch.
- **Returns:** `string` (Markdown-formatted content)

---
*RepoForge Engine v0.3 - Tool Schemas Verified.*
