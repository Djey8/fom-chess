# Jira Ticket Operations

Use the local Jira client from the repository root.

## 1. Replace the local PAT first

If the PAT in `tools/jira/jira.local.json` was exposed in terminal output, replace it directly in that local file before any further Jira read or write.

## 2. Discover the Epic field

For Jira Data Center projects, child issues are often linked to an Epic via a custom field such as `customfield_10014`.

Preview the available Epic-related fields:

```powershell
python -m tools.jira.client fields --name epic
```

## 3. Preview Epic and ticket updates

Preview an update to UC-1 or UC-2:

```powershell
python -m tools.jira.client update UC-1 --summary "<new summary>" --description-file .\docs\jira-ticket-pack.md
python -m tools.jira.client update UC-2 --summary "<new summary>" --description "<new description>"
```

Preview a new child ticket with an Epic link field payload:

```powershell
python -m tools.jira.client create \
  --summary "UC-3 Implement full castling legality checks" \
  --description "<ticket description>" \
  --issue-type Task \
  --fields-file .\tools\jira\epic-link.local.json
```

Example content for `tools/jira/epic-link.local.json` after discovering the correct Epic field id:

```json
{
  "customfield_10014": "UC-1"
}
```

## 4. Apply only after reviewing the preview

Repeat the exact approved command with `--send`.

Examples:

```powershell
python -m tools.jira.client update UC-1 --summary "<new summary>" --description-file .\docs\jira-ticket-pack.md --send
python -m tools.jira.client create --summary "UC-3 Implement full castling legality checks" --description "<ticket description>" --fields-file .\tools\jira\epic-link.local.json --send
```