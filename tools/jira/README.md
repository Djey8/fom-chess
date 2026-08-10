# Jira project automation

This self-contained, standard-library package provides controlled Jira reads
and preview-by-default writes. Run commands from the repository root with
`python -m tools.jira.client`.

Create `jira.local.json` beside this file from `jira.local.example.json`, then
enter the PAT directly in the ignored local file. Never provide credentials
through chat, logs, commits, issues, or screenshots.

Set `base_url` to the Jira application root. If issue URLs look like
`https://jira.example.com/agile/browse/PROJECT-123`, use
`https://jira.example.com/agile`, not only the host. An HTML/Tomcat `404` from
the API root usually indicates a missing application context path.

Use `allowed_issue_keys` to limit the client to exact tickets:

```json
"allowed_issue_keys": ["PROJECT-123", "PROJECT-456"]
```

The scope applies to reads, searches, comments, and transitions. Searches are
automatically intersected with the configured keys. An empty list denies every
ticket operation. Omitting the setting or using `null` disables ticket scoping
for backward compatibility. Issue creation is disabled while a scope is active.

Read-only examples:

```powershell
python -m tools.jira.client check
python -m tools.jira.client get PROJECT-123
python -m tools.jira.client comments PROJECT-123
python -m tools.jira.client comments PROJECT-123 --author username --latest
python -m tools.jira.client search --jql "project = PROJECT ORDER BY updated DESC"
python -m tools.jira.client transitions PROJECT-123
```

Writes print their exact payload unless `--send` is present:

```powershell
python -m tools.jira.client comment PROJECT-123 --body-file update.md
python -m tools.jira.client transition PROJECT-123 --to "In Progress"
```

After review and explicit approval, repeat the same command with `--send`, then
read the latest comment and issue status again to verify the comment ID, author,
timestamp, exact approved body, and resulting status. Use an ignored
`ISSUE-comment.local.txt` file for comment drafts and delete it after verification.
If the current status is already appropriate, apply no transition. If a token is
ever exposed, revoke and replace it before performing another Jira write.