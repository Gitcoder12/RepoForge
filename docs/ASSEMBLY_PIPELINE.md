# Five-Stage Project Assembly Pipeline

RepoForge includes a provider-neutral, five-stage workflow for producing reviewable project artifacts with any AI model that can follow text instructions.

## Stages

1. **Blueprint** — architecture, interfaces, file tree, dependencies, risks, and acceptance criteria. No implementation code.
2. **Foundation** — typed schemas, configuration, persistence, and environment setup based on the approved blueprint.
3. **Engine** — core business logic, APIs, integration contracts, and focused tests.
4. **Shield** — threat model, tests for normal and adversarial cases, and applicable security controls.
5. **Deployment** — containerization, CI, local operation instructions, and a release verification checklist.

Each stage produces an artifact that is stored in a local state file. The next stage remains locked until the current artifact is explicitly approved. Rejected artifacts can be revised using recorded feedback.

## Start a project

Run the command from the installed RepoForge environment:

```bash
repoforge pipeline init \
  --project-name "Example Service" \
  --description "A service that solves a defined user problem" \
  --target-environment "Docker on AWS" \
  --stack "Python 3.12, FastAPI, PostgreSQL" \
  --edge-cases "Concurrent requests, timeouts, malformed input"
```

The default state file is `.repoforge/assembly.json`. It contains the project brief and every submitted stage artifact. Keep it out of public repositories and do not include credentials or private data in prompts or artifacts.

## Work through the stages

Generate the current prompt:

```bash
repoforge pipeline prompt
```

Send the entire prompt to the AI model of your choice. Save its complete response as a UTF-8 text file, then submit it:

```bash
repoforge pipeline submit --artifact-file blueprint.txt
```

Review the stored artifact before approving it. The next stage is unlocked only after approval:

```bash
repoforge pipeline approve --note "Architecture and interfaces reviewed"
repoforge pipeline prompt
```

Reject a submission to request a revision:

```bash
repoforge pipeline reject --feedback "Define error contracts and data retention"
repoforge pipeline prompt
```

Inspect progress at any time:

```bash
repoforge pipeline status
```

Use `--state-file PATH` with any pipeline command to work with a different state file.

## Quality boundaries

- The workflow stores artifacts and manages stage approvals. It does not automatically execute generated code or modify a target repository.
- Human approval is a sequencing gate, not proof of correctness.
- Model-generated tests must be run in the actual project environment.
- Security controls must be selected against the project's real threat model; no system can be declared hack-proof.
- Citation and factual claims must be independently checked against primary sources.
- Production readiness requires successful builds, tests, security review, deployment checks, monitoring, and operational ownership. Completing the five prompt stages is not a production-readiness certificate.
- Do not put secrets, personal data, proprietary source code, or confidential customer information into providers unless their data-handling terms permit it.

The purpose of the pipeline is to reduce context loss and uncontrolled scope while keeping architecture, implementation, validation, and deployment decisions reviewable.
