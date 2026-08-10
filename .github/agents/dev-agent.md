---
name: dev-agent
description: Repository coding agent for Jira-driven GitHub issues and pull requests in this project.
model: GPT-5.6 Luna (copilot)
tools: [read, edit, search, execute]
user-invocable: false
---

# Copilot Coding Agent Instructions

You are an autonomous coding agent for this repository.

## General Rules
- Always create or update unit tests when changing logic.
- Prefer small, incremental changes.
- Never modify unrelated files.
- Follow existing code structure and style.
- Do not introduce new dependencies unless explicitly requested.

## Jira Ticket Knowledge
- Use `tools/jira_knowledge.json` as the source of truth when drafting or validating Jira tickets.
- Run `python tools/jira_knowledge.py validate` before relying on the knowledge database.
- Apply the issue-type template, acceptance criteria policy, Definition of Ready, and Definition of Done.
- Never store credentials or tokens in the knowledge database.
- For the approved web expansion, trace work through `doc/requirements.md`, `doc/target-architecture.md`, `doc/delivery-plan.md`, and `tools/jira_backlog.json`.
- Preserve requirement IDs and Plan IDs in implementation tests, pull requests, and Jira updates.
- Do not change an architecture decision or non-goal without updating the source documents first.

## Python Rules
- Use type hints.
- Follow PEP8.
- Prefer pure functions.
- Keep functions under 40 lines when practical.

## PR Expectations
- PR must match the pull request template.
- Reference the GitHub Issue.
- Explain reasoning briefly.