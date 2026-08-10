import argparse
import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from urllib.parse import parse_qs, urlsplit

try:
    from tools.jira.client import ConfigError, JiraClient, JiraConfig, _run
except ModuleNotFoundError:
    from client import ConfigError, JiraClient, JiraConfig, _run


def _config(allowed_issue_keys: tuple[str, ...] | None) -> JiraConfig:
    return JiraConfig(
        base_url="https://jira.example.com",
        api_path="/rest/api/2",
        personal_access_token="test-only",
        timeout_seconds=1.0,
        ca_bundle=None,
        default_project_key="PROJECT",
        default_issue_type="Task",
        default_labels=(),
        allowed_issue_keys=allowed_issue_keys,
    )


class RecordingClient(JiraClient):
    def __init__(self, allowed_issue_keys: tuple[str, ...] | None) -> None:
        super().__init__(_config(allowed_issue_keys))
        self.calls: list[tuple[str, str, dict[str, object] | None]] = []

    def _request(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> dict[str, object]:
        self.calls.append((method, path, payload))
        if path == "/field":
            return [
                {"id": "summary", "name": "Summary"},
                {"id": "customfield_10014", "name": "Epic Link"},
            ]
        if path.startswith("/search?"):
            return {"issues": []}
        if "/comment?" in path:
            return {
                "comments": [
                    {
                        "id": "1",
                        "author": {"name": "other", "displayName": "Other User"},
                        "created": "2026-01-01T10:00:00.000+0000",
                        "updated": "2026-01-01T10:00:00.000+0000",
                        "body": "Earlier",
                    },
                    {
                        "id": "2",
                        "author": {"name": "developer", "displayName": "Developer"},
                        "created": "2026-01-02T10:00:00.000+0000",
                        "updated": "2026-01-02T10:00:00.000+0000",
                        "body": "Latest",
                    },
                ]
            }
        if method == "GET" and path.endswith("/transitions"):
            return {"transitions": []}
        return {}


class TicketScopeTests(unittest.TestCase):
    def test_allowed_key_is_normalized_for_issue_operations(self) -> None:
        client = RecordingClient(("PROJECT-123",))

        client.get_issue("project-123", ("summary",))
        client.add_comment("project-123", "Update")
        client.available_transitions("project-123")
        client.transition_issue("project-123", "31")

        self.assertEqual(len(client.calls), 4)
        self.assertTrue(all("PROJECT-123" in call[1] for call in client.calls))

    def test_denied_key_never_reaches_request_layer(self) -> None:
        client = RecordingClient(("PROJECT-123",))
        operations = (
            lambda: client.get_issue("PROJECT-999", ("summary",)),
            lambda: client.add_comment("PROJECT-999", "Update"),
            lambda: client.available_transitions("PROJECT-999"),
            lambda: client.transition_issue("PROJECT-999", "31"),
        )

        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(ConfigError, "outside.*scope"):
                    operation()

        self.assertEqual(client.calls, [])

    def test_comment_preview_rejects_denied_key(self) -> None:
        client = RecordingClient(("PROJECT-123",))
        args = argparse.Namespace(
            command="comment",
            issue_key="PROJECT-999",
            body="Update",
            body_file=None,
            send=False,
        )

        with self.assertRaisesRegex(ConfigError, "outside.*scope"):
            _run(client, args)

        self.assertEqual(client.calls, [])

    def test_comment_history_is_scoped(self) -> None:
        client = RecordingClient(("PROJECT-123",))

        comments = client.get_comments("project-123", 1000)

        self.assertEqual([comment["id"] for comment in comments], ["1", "2"])
        self.assertIn("/issue/PROJECT-123/comment?maxResults=1000", client.calls[0][1])

        with self.assertRaisesRegex(ConfigError, "outside.*scope"):
            client.get_comments("PROJECT-999", 1000)

        self.assertEqual(len(client.calls), 1)

    def test_comments_command_filters_author_and_latest(self) -> None:
        client = RecordingClient(("PROJECT-123",))
        args = argparse.Namespace(
            command="comments",
            issue_key="PROJECT-123",
            author="developer",
            latest=True,
            max_results=1000,
        )

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(_run(client, args), 0)

        result = json.loads(output.getvalue())
        self.assertEqual(result["comments"][0]["id"], "2")
        self.assertNotIn("emailAddress", output.getvalue())
        self.assertEqual(len(client.calls), 1)

    def test_search_is_intersected_with_allowed_keys(self) -> None:
        client = RecordingClient(("PROJECT-123", "PROJECT-456"))

        client.search_issues("project = PROJECT", ("summary",), 10)

        query = parse_qs(urlsplit(client.calls[0][1]).query)
        self.assertEqual(
            query["jql"],
            ["(project = PROJECT) AND key in (PROJECT-123, PROJECT-456)"],
        )

    def test_scoped_search_preserves_top_level_order_by(self) -> None:
        client = RecordingClient(("PROJECT-123",))

        client.search_issues(
            'summary ~ "order by design" ORDER BY updated DESC', ("summary",), 10
        )

        query = parse_qs(urlsplit(client.calls[0][1]).query)
        self.assertEqual(
            query["jql"],
            [
                '(summary ~ "order by design") AND key in (PROJECT-123) '
                "ORDER BY updated DESC"
            ],
        )

    def test_invalid_allowed_key_is_rejected_before_search(self) -> None:
        client = RecordingClient(("PROJECT-123) OR project = OTHER",))

        with self.assertRaisesRegex(ConfigError, "issue key must look like"):
            client.search_issues("project = PROJECT", ("summary",), 10)

        self.assertEqual(client.calls, [])

    def test_empty_scope_denies_search_without_request(self) -> None:
        client = RecordingClient(())

        self.assertEqual(client.search_issues("project = PROJECT", ("summary",), 10), [])
        self.assertEqual(client.calls, [])

    def test_scope_disables_issue_creation(self) -> None:
        client = RecordingClient(("PROJECT-123",))

        with self.assertRaisesRegex(ConfigError, "creation is disabled"):
            client.build_issue_payload("Summary", "Description")

    def test_create_payload_merges_extra_fields(self) -> None:
        client = RecordingClient(None)

        payload = client.build_issue_payload(
            "Summary",
            "Description",
            extra_fields={"customfield_10014": "PROJECT-1"},
        )

        self.assertEqual(payload["fields"]["customfield_10014"], "PROJECT-1")

    def test_update_payload_requires_scope_and_field_changes(self) -> None:
        client = RecordingClient(("PROJECT-123",))

        issue_key, payload = client.build_issue_update_payload(
            "project-123",
            summary="Updated summary",
            extra_fields={"customfield_10014": "PROJECT-1"},
        )

        self.assertEqual(issue_key, "PROJECT-123")
        self.assertEqual(payload["fields"]["summary"], "Updated summary")
        self.assertEqual(payload["fields"]["customfield_10014"], "PROJECT-1")

        with self.assertRaisesRegex(ConfigError, "at least one field change"):
            client.build_issue_update_payload("PROJECT-123")

    def test_update_preview_rejects_denied_key(self) -> None:
        client = RecordingClient(("PROJECT-123",))
        args = argparse.Namespace(
            command="update",
            issue_key="PROJECT-999",
            summary="Updated summary",
            description=None,
            description_file=None,
            fields_file=None,
            send=False,
        )

        with self.assertRaisesRegex(ConfigError, "outside.*scope"):
            _run(client, args)

        self.assertEqual(client.calls, [])

    def test_fields_command_can_filter_results(self) -> None:
        client = RecordingClient(None)
        args = argparse.Namespace(command="fields", name="epic")

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(_run(client, args), 0)

        result = json.loads(output.getvalue())
        self.assertEqual(result["fields"][0]["id"], "customfield_10014")


if __name__ == "__main__":
    unittest.main()