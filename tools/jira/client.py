#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DEFAULT_CONFIG_PATH = Path(__file__).with_name("jira.local.json")
TOKEN_PLACEHOLDER = "REPLACE_WITH_YOUR_JIRA_PAT"
DEFAULT_FIELDS = ("summary", "status", "description", "labels", "assignee")
JsonObject = dict[str, Any]
JsonValue = dict[str, Any] | list[Any]


class ConfigError(ValueError):
    """Raised when the local Jira configuration is missing or invalid."""


class JiraError(RuntimeError):
    """Raised when Jira cannot complete an API request."""


@dataclass(frozen=True)
class JiraConfig:
    base_url: str
    api_path: str
    personal_access_token: str
    timeout_seconds: float
    ca_bundle: str | None
    default_project_key: str
    default_issue_type: str
    default_labels: tuple[str, ...]
    allowed_issue_keys: tuple[str, ...] | None = None
    auth_email: str | None = None

    @property
    def api_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.api_path.strip('/')}"

    @classmethod
    def from_file(cls, path: Path) -> JiraConfig:
        data = _load_json_object(path)
        base_url = _required_string(data, "base_url")
        token = _required_string(data, "personal_access_token")
        if not base_url.startswith("https://"):
            raise ConfigError("base_url must use HTTPS")
        if token == TOKEN_PLACEHOLDER:
            raise ConfigError(f"Replace the token placeholder in {path}")

        ca_bundle = _optional_string(data, "ca_bundle")
        if ca_bundle and not Path(ca_bundle).is_absolute():
            ca_bundle = str((path.parent / ca_bundle).resolve())

        return cls(
            base_url=base_url,
            api_path=_string_value(data, "api_path", "/rest/api/2"),
            personal_access_token=token,
            timeout_seconds=_positive_number(data, "timeout_seconds", 20.0),
            ca_bundle=ca_bundle,
            default_project_key=_required_string(data, "default_project_key"),
            default_issue_type=_string_value(data, "default_issue_type", "Task"),
            default_labels=_string_tuple(data, "default_labels"),
            allowed_issue_keys=_optional_issue_keys(data, "allowed_issue_keys"),
            auth_email=_optional_string(data, "auth_email"),
        )


class JiraClient:
    def __init__(self, config: JiraConfig) -> None:
        self._config = config

    def check_connection(self) -> JsonObject:
        return self._request("GET", "/myself")

    def check_permissions(self, project_key: str | None = None) -> JsonObject:
        query = urlencode(
            {
                "projectKey": project_key or self._config.default_project_key,
                "permissions": "BROWSE_PROJECTS,CREATE_ISSUES",
            }
        )
        return self._request("GET", f"/mypermissions?{query}")

    def get_fields(self) -> list[JsonObject]:
        response = self._request("GET", "/field")
        if not isinstance(response, list) or not all(isinstance(field, dict) for field in response):
            raise JiraError("Jira returned an unexpected field list")
        return response

    def _allowed_issue_keys(self) -> tuple[str, ...] | None:
        configured_keys = self._config.allowed_issue_keys
        if configured_keys is None:
            return None
        return tuple(dict.fromkeys(_normalize_issue_key(key) for key in configured_keys))

    def require_issue_allowed(self, issue_key: str) -> str:
        normalized_key = _normalize_issue_key(issue_key)
        allowed_keys = self._allowed_issue_keys()
        if allowed_keys is not None and normalized_key not in allowed_keys:
            raise ConfigError(
                f"Issue {normalized_key} is outside the configured allowed_issue_keys scope"
            )
        return normalized_key

    def get_issue(self, issue_key: str, fields: tuple[str, ...]) -> JsonObject:
        issue_key = self.require_issue_allowed(issue_key)
        query = urlencode({"fields": ",".join(fields)})
        return self._request("GET", f"/issue/{_issue_key(issue_key)}?{query}")

    def get_comments(self, issue_key: str, max_results: int) -> list[JsonObject]:
        issue_key = self.require_issue_allowed(issue_key)
        query = urlencode({"maxResults": max_results})
        response = self._request(
            "GET", f"/issue/{_issue_key(issue_key)}/comment?{query}"
        )
        comments = response.get("comments")
        if not isinstance(comments, list) or not all(
            isinstance(comment, dict) for comment in comments
        ):
            raise JiraError("Jira returned an unexpected comment list")
        return comments

    def search_issues(
        self, jql: str, fields: tuple[str, ...], max_results: int
    ) -> list[JsonObject]:
        allowed_keys = self._allowed_issue_keys()
        if allowed_keys == ():
            return []
        if allowed_keys is not None:
            jql = _scope_jql(jql, allowed_keys)
        query = urlencode(
            {"jql": jql, "fields": ",".join(fields), "maxResults": max_results}
        )
        response = self._request("GET", f"/search?{query}")
        issues = response.get("issues")
        if not isinstance(issues, list) or not all(isinstance(issue, dict) for issue in issues):
            raise JiraError("Jira search returned an unexpected issue list")
        return issues

    def build_issue_payload(
        self,
        summary: str,
        description: str,
        project_key: str | None = None,
        issue_type: str | None = None,
        labels: tuple[str, ...] = (),
        extra_fields: JsonObject | None = None,
    ) -> JsonObject:
        if self._config.allowed_issue_keys is not None:
            raise ConfigError(
                "Issue creation is disabled when allowed_issue_keys is configured"
            )
        clean_summary = summary.strip()
        if not clean_summary:
            raise ConfigError("summary must not be empty")
        merged_labels = tuple(dict.fromkeys((*self._config.default_labels, *labels)))
        fields: JsonObject = {
            "project": {"key": project_key or self._config.default_project_key},
            "issuetype": {"name": issue_type or self._config.default_issue_type},
            "summary": clean_summary,
            "description": description.strip(),
            "labels": list(merged_labels),
        }
        if extra_fields is not None:
            fields.update(extra_fields)
        return {"fields": fields}

    def build_issue_update_payload(
        self,
        issue_key: str,
        summary: str | None = None,
        description: str | None = None,
        extra_fields: JsonObject | None = None,
    ) -> tuple[str, JsonObject]:
        normalized_key = self.require_issue_allowed(issue_key)
        fields: JsonObject = {}
        if summary is not None:
            clean_summary = summary.strip()
            if not clean_summary:
                raise ConfigError("summary must not be empty")
            fields["summary"] = clean_summary
        if description is not None:
            fields["description"] = description.strip()
        if extra_fields is not None:
            fields.update(extra_fields)
        if not fields:
            raise ConfigError("update requires at least one field change")
        return normalized_key, {"fields": fields}

    def create_issue(self, payload: JsonObject) -> JsonObject:
        return self._request("POST", "/issue", payload)

    def update_issue(self, issue_key: str, payload: JsonObject) -> JsonObject:
        issue_key = self.require_issue_allowed(issue_key)
        return self._request("PUT", f"/issue/{_issue_key(issue_key)}", payload)

    def add_comment(self, issue_key: str, body: str) -> JsonObject:
        issue_key = self.require_issue_allowed(issue_key)
        return self._request(
            "POST", f"/issue/{_issue_key(issue_key)}/comment", {"body": body}
        )

    def available_transitions(self, issue_key: str) -> list[JsonObject]:
        issue_key = self.require_issue_allowed(issue_key)
        response = self._request("GET", f"/issue/{_issue_key(issue_key)}/transitions")
        transitions = response.get("transitions")
        if not isinstance(transitions, list) or not all(
            isinstance(transition, dict) for transition in transitions
        ):
            raise JiraError("Jira returned an unexpected transition list")
        return transitions

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        issue_key = self.require_issue_allowed(issue_key)
        self._request(
            "POST",
            f"/issue/{_issue_key(issue_key)}/transitions",
            {"transition": {"id": transition_id}},
        )

    def _request(
        self, method: str, path: str, payload: JsonObject | None = None
    ) -> JsonValue:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Accept": "application/json",
            "Authorization": _authorization_header(self._config),
            "User-Agent": "atlas-jira-project-automation/1.0",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(
            f"{self._config.api_url}/{path.lstrip('/')}",
            data=body,
            headers=headers,
            method=method,
        )
        context = ssl.create_default_context(cafile=self._config.ca_bundle)
        return _open_json(request, self._config.timeout_seconds, context)


def _authorization_header(config: JiraConfig) -> str:
    if config.auth_email:
        credentials = f"{config.auth_email}:{config.personal_access_token}".encode("utf-8")
        return f"Basic {base64.b64encode(credentials).decode('ascii')}"
    return f"Bearer {config.personal_access_token}"


def _open_json(request: Request, timeout: float, context: ssl.SSLContext) -> JsonValue:
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as error:
        detail = _error_detail(error.read().decode("utf-8", errors="replace"))
        raise JiraError(f"Jira returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise JiraError(f"Could not reach Jira: {error.reason}") from error

    if not raw_body:
        return {}
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise JiraError("Jira returned invalid JSON") from error
    if not isinstance(data, (dict, list)):
        raise JiraError("Jira returned an unexpected JSON value")
    return data


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read Jira issues and preview or apply controlled Jira writes."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Verify connectivity and project permissions.")

    get = commands.add_parser("get", help="Read an issue.")
    get.add_argument("issue_key")
    get.add_argument("--field", action="append", default=[])

    comments = commands.add_parser("comments", help="Read concise issue comments.")
    comments.add_argument("issue_key")
    comments.add_argument("--author")
    comments.add_argument("--latest", action="store_true")
    comments.add_argument("--max-results", type=int, default=1000)

    search = commands.add_parser("search", help="Search issues with JQL.")
    search.add_argument("--jql", required=True)
    search.add_argument("--field", action="append", default=[])
    search.add_argument("--max-results", type=int, default=50)

    fields = commands.add_parser("fields", help="List available Jira fields.")
    fields.add_argument("--name")

    create = commands.add_parser("create", help="Preview or create an issue.")
    create.add_argument("--summary", required=True)
    create_body = create.add_mutually_exclusive_group()
    create_body.add_argument("--description", default="")
    create_body.add_argument("--description-file", type=Path)
    create.add_argument("--project")
    create.add_argument("--issue-type")
    create.add_argument("--label", action="append", default=[])
    create.add_argument("--fields-file", type=Path)
    create.add_argument("--send", action="store_true")

    update = commands.add_parser("update", help="Preview or update an existing issue.")
    update.add_argument("issue_key")
    update.add_argument("--summary")
    update_body = update.add_mutually_exclusive_group()
    update_body.add_argument("--description")
    update_body.add_argument("--description-file", type=Path)
    update.add_argument("--fields-file", type=Path)
    update.add_argument("--send", action="store_true")

    comment = commands.add_parser("comment", help="Preview or add a comment.")
    comment.add_argument("issue_key")
    comment_body = comment.add_mutually_exclusive_group(required=True)
    comment_body.add_argument("--body")
    comment_body.add_argument("--body-file", type=Path)
    comment.add_argument("--send", action="store_true")

    transitions = commands.add_parser("transitions", help="List available transitions.")
    transitions.add_argument("issue_key")

    transition = commands.add_parser("transition", help="Preview or apply a transition.")
    transition.add_argument("issue_key")
    transition.add_argument("--to", required=True)
    transition.add_argument("--send", action="store_true")
    return parser


def _run(client: JiraClient, args: argparse.Namespace) -> int:
    if args.command == "check":
        identity = client.check_connection()
        permissions = client.check_permissions()
        _print_json(_connection_summary(identity, permissions))
        return 0
    if args.command == "get":
        _print_json(client.get_issue(args.issue_key, _fields(args.field)))
        return 0
    if args.command == "comments":
        if args.max_results <= 0:
            raise ConfigError("max-results must be positive")
        comments = client.get_comments(args.issue_key, args.max_results)
        if args.author:
            comments = [
                comment
                for comment in comments
                if _comment_matches_author(comment, args.author)
            ]
        if args.latest:
            comments = sorted(comments, key=lambda comment: str(comment.get("created", "")))[
                -1:
            ]
        _print_json({"comments": [_comment_summary(comment) for comment in comments]})
        return 0
    if args.command == "search":
        if args.max_results <= 0:
            raise ConfigError("max-results must be positive")
        _print_json(
            {"issues": client.search_issues(args.jql, _fields(args.field), args.max_results)}
        )
        return 0
    if args.command == "fields":
        fields = client.get_fields()
        if args.name:
            requested = args.name.strip().casefold()
            fields = [
                field
                for field in fields
                if requested in str(field.get("name", "")).casefold()
                or requested in str(field.get("id", "")).casefold()
            ]
        _print_json({"fields": fields})
        return 0
    if args.command == "create":
        payload = client.build_issue_payload(
            args.summary,
            _optional_text_arg(args.description, args.description_file),
            args.project,
            args.issue_type,
            tuple(args.label),
            _optional_json_file(args.fields_file),
        )
        return _preview_or_send(
            "create", payload, args.send, lambda: client.create_issue(payload)
        )
    if args.command == "update":
        issue_key, payload = client.build_issue_update_payload(
            args.issue_key,
            args.summary,
            _optional_text_arg(args.description, args.description_file),
            _optional_json_file(args.fields_file),
        )
        return _preview_or_send(
            "update", payload, args.send, lambda: client.update_issue(issue_key, payload)
        )
    if args.command == "comment":
        body = _comment_body(args).strip()
        if not body:
            raise ConfigError("comment body must not be empty")
        issue_key = client.require_issue_allowed(args.issue_key)
        payload = {"issue_key": issue_key, "body": body}
        return _preview_or_send(
            "comment", payload, args.send, lambda: client.add_comment(issue_key, body)
        )
    if args.command == "transitions":
        _print_json({"transitions": client.available_transitions(args.issue_key)})
        return 0
    if args.command == "transition":
        transition = _find_transition(client.available_transitions(args.issue_key), args.to)
        payload = {
            "issue_key": args.issue_key,
            "transition": {"id": transition.get("id"), "name": transition.get("name")},
        }
        return _preview_or_send(
            "transition",
            payload,
            args.send,
            lambda: client.transition_issue(args.issue_key, str(transition["id"])),
        )
    raise ConfigError(f"Unsupported command: {args.command}")


def _preview_or_send(
    operation: str, payload: JsonObject, send: bool, action: Any
) -> int:
    if not send:
        _print_json({"preview": True, "operation": operation, "payload": payload})
        return 0
    result = action()
    _print_json({"status": "applied", "operation": operation, "result": result or {}})
    return 0


def _comment_body(args: argparse.Namespace) -> str:
    if args.body is not None:
        return str(args.body)
    try:
        return args.body_file.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise ConfigError(f"Comment file not found: {args.body_file}") from error


def _optional_text_arg(value: str | None, path: Path | None) -> str | None:
    if path is not None:
        try:
            return path.read_text(encoding="utf-8-sig")
        except FileNotFoundError as error:
            raise ConfigError(f"Text file not found: {path}") from error
    return value


def _optional_json_file(path: Path | None) -> JsonObject | None:
    if path is None:
        return None
    return _load_json_object(path)


def _comment_matches_author(comment: JsonObject, requested_author: str) -> bool:
    author = comment.get("author")
    if not isinstance(author, dict):
        return False
    requested = requested_author.strip().casefold()
    identities = (author.get("name"), author.get("accountId"), author.get("displayName"))
    return any(
        isinstance(identity, str) and identity.casefold() == requested
        for identity in identities
    )


def _comment_summary(comment: JsonObject) -> JsonObject:
    author = comment.get("author")
    if not isinstance(author, dict):
        author = {}
    return {
        "id": comment.get("id"),
        "author": author.get("displayName"),
        "username": author.get("name") or author.get("accountId"),
        "created": comment.get("created"),
        "updated": comment.get("updated"),
        "body": comment.get("body"),
    }


def _find_transition(transitions: list[JsonObject], requested_name: str) -> JsonObject:
    matches = [
        transition
        for transition in transitions
        if str(transition.get("name", "")).casefold() == requested_name.strip().casefold()
    ]
    if len(matches) == 1 and matches[0].get("id") is not None:
        return matches[0]
    available = ", ".join(str(item.get("name")) for item in transitions) or "none"
    raise ConfigError(
        f"Transition '{requested_name}' is not uniquely available. Available: {available}"
    )


def _fields(values: list[str]) -> tuple[str, ...]:
    fields = tuple(value.strip() for value in values if value.strip())
    return fields or DEFAULT_FIELDS


def _issue_key(value: str) -> str:
    return quote(_normalize_issue_key(value), safe="")


def _normalize_issue_key(value: str) -> str:
    clean_value = value.strip().upper()
    project_key, separator, issue_number = clean_value.partition("-")
    valid_project = bool(project_key) and "A" <= project_key[0] <= "Z" and all(
        "A" <= character <= "Z" or "0" <= character <= "9" or character == "_"
        for character in project_key
    )
    valid_number = bool(issue_number) and all(
        "0" <= character <= "9" for character in issue_number
    )
    if separator != "-" or not valid_project or not valid_number:
        raise ConfigError("issue key must look like PROJECT-123")
    return clean_value


def _scope_jql(jql: str, allowed_keys: tuple[str, ...]) -> str:
    filter_clause, order_clause = _split_jql_order_by(jql)
    if not filter_clause:
        raise ConfigError("jql must contain a filter before ORDER BY")
    key_scope = ", ".join(allowed_keys)
    scoped_jql = f"({filter_clause}) AND key in ({key_scope})"
    return f"{scoped_jql} {order_clause}" if order_clause else scoped_jql


def _split_jql_order_by(jql: str) -> tuple[str, str | None]:
    clean_jql = jql.strip()
    quote_character: str | None = None
    escaped = False
    parenthesis_depth = 0
    lowered_jql = clean_jql.casefold()
    for index, character in enumerate(clean_jql):
        if quote_character is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote_character:
                quote_character = None
            continue
        if character in ("'", '"'):
            quote_character = character
        elif character == "(":
            parenthesis_depth += 1
        elif character == ")":
            parenthesis_depth = max(0, parenthesis_depth - 1)
        elif parenthesis_depth == 0 and lowered_jql.startswith("order by", index):
            before_is_boundary = index == 0 or clean_jql[index - 1].isspace()
            after_index = index + len("order by")
            after_is_boundary = (
                after_index == len(clean_jql) or clean_jql[after_index].isspace()
            )
            if before_is_boundary and after_is_boundary:
                return clean_jql[:index].strip(), clean_jql[index:].strip()
    return clean_jql, None


def _load_json_object(path: Path) -> JsonObject:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as error:
        raise ConfigError(f"Configuration file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"Invalid JSON in {path}: {error.msg}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration root must be a JSON object: {path}")
    return data


def _required_string(data: JsonObject, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be a non-empty string")
    return value.strip()


def _string_value(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_string(data: JsonObject, key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} must be null or a non-empty string")
    return value.strip()


def _positive_number(data: JsonObject, key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{key} must be a positive number")
    return float(value)


def _string_tuple(data: JsonObject, key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be an array of strings")
    return tuple(item.strip() for item in value if item.strip())


def _optional_issue_keys(data: JsonObject, key: str) -> tuple[str, ...] | None:
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be null or an array of issue keys")
    return tuple(dict.fromkeys(_normalize_issue_key(item) for item in value))


def _error_detail(raw_body: str) -> str:
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        return raw_body.strip() or "No error details"
    if not isinstance(data, dict):
        return "No error details"
    messages = data.get("errorMessages", [])
    errors = data.get("errors", {})
    details = [str(message) for message in messages] if isinstance(messages, list) else []
    if isinstance(errors, dict):
        details.extend(f"{key}: {value}" for key, value in errors.items())
    return "; ".join(details) or "No error details"


def _has_permission(response: JsonObject, permission: str) -> bool:
    permissions = response.get("permissions")
    if not isinstance(permissions, dict):
        return False
    details = permissions.get(permission)
    return isinstance(details, dict) and details.get("havePermission") is True


def _connection_summary(identity: JsonObject, permissions: JsonObject) -> JsonObject:
    return {
        "status": "ok",
        "display_name": identity.get("displayName"),
        "username": identity.get("name") or identity.get("accountId"),
        "permissions": {
            "browse_projects": _has_permission(permissions, "BROWSE_PROJECTS"),
            "create_issues": _has_permission(permissions, "CREATE_ISSUES"),
        },
    }


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _run(JiraClient(JiraConfig.from_file(args.config)), args)
    except (ConfigError, JiraError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())