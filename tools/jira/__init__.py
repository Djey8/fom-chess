from typing import Any

__all__ = ["ConfigError", "JiraClient", "JiraConfig", "JiraError", "main"]


def __getattr__(name: str) -> Any:
	if name not in __all__:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
	from tools.jira import client

	return getattr(client, name)