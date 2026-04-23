# Repository Navigation Agents

This workspace contains a small set of local VS Code custom agents for repository analysis, ETL quality review, and public GitHub inspection.

## Agents

### Data Blaster
Use for local repository analysis.
- Summarizes repository structure
- Maps dependencies and architecture
- Traces data flow and main entry points
- Highlights ML-related components

### ETL Quality Sentinel
Use for ETL and data-quality review.
- Checks schema drift
- Reviews missing values, duplicates, and freshness risks
- Looks for validation gaps and pipeline quality issues
- Calls out ML impact when data quality affects training or inference

### GitHub Repo Scout
Use for public GitHub repository inspection.
- Summarizes public repo structure
- Reviews dependency clues from public files
- Explains architecture from reachable source material
- Notes any access limits if the repository is incomplete or private

### Repository Navigator
Use as the single entry point when you are not sure which specialist to start with.
- Routes local repo analysis to Data Blaster
- Routes quality checks to ETL Quality Sentinel
- Routes public GitHub inspection to GitHub Repo Scout

## Recommended Test Flow

1. Start with `Repository Navigator`.
2. Route to `Data Blaster` for a broad repo summary.
3. Follow the handoff to `ETL Quality Sentinel` for quality and validation review.
4. Use `GitHub Repo Scout` when the target is a public GitHub repo.

## Sample Prompts

### Repository Navigator
"Analyze this repository and route me to the right specialist. I want a summary of the architecture, main entry points, and any data pipeline or ML-related components that look important."

### Data Blaster
"Summarize this repository's structure, dependencies, and architecture. Focus on the main entry points, data flow, and any ML-related components that are important. Call out the key files and the paths where the main logic starts."

### ETL Quality Sentinel
"Inspect the pipeline or dataset for data quality risks, schema drift, missing values, duplicates, freshness problems, and validation gaps that could affect ML. Call out confirmed issues, likely risks, and the exact files or checks that support them."

### GitHub Repo Scout
"Review this public GitHub repository and summarize its structure, dependencies, and architecture. Focus on the main entry points, public files, and any clues about how the code is organized. Call out any limits if the source is incomplete or not publicly accessible."

## Status

- The agent files are local to this workspace.
- Handoffs are wired between the specialist agents.
- The agent guide now lives in [AGENTS.md](AGENTS.md).