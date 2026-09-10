import pytest

from app.core.resource import InvalidResourceId, ResourceId, parse_resource_id


@pytest.mark.parametrize(
    "raw,rtype,value",
    [
        ("project:agent-os", "project", "agent-os"),
        ("repo:owner/name", "repo", "owner/name"),
        ("device:desktop-main", "device", "desktop-main"),
        ("service:cloudflare", "service", "cloudflare"),
        ("secretref:openai/main", "secretref", "openai/main"),
        ("task:2f1c9a", "task", "2f1c9a"),
        ("local:reasoning", "local", "reasoning"),
    ],
)
def test_valid_resource_ids(raw, rtype, value):
    rid = parse_resource_id(raw)
    assert rid == ResourceId(rtype, value)
    assert str(rid) == raw


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "*",
        "project:*",
        "project:a*b",
        "no-colon",
        "unknown:thing",
        "PROJECT:agent-os",
        "project: agent-os",
        " project:agent-os",
        "repo:owner",  # repo needs exactly one slash
        "repo:owner/name/extra",
        "project:../escape",
        "device:a/b",  # slash only allowed for repo/secretref
        "project:UPPER",
        123,
        None,
    ],
)
def test_invalid_resource_ids(raw):
    with pytest.raises(InvalidResourceId):
        parse_resource_id(raw)
