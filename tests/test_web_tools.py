"""Web tool boundaries, saved retrieval evidence and opt-in policy; no network."""

import hashlib
from urllib.parse import parse_qs, urlsplit

import pytest

from proof_eval.evidence.io import fingerprint, now, write_jsonl
from proof_eval.harness import cli, web
from proof_eval.harness.config import RunConfig
from proof_eval.harness.configuration import load_inputs
from proof_eval.harness.prompts import WEB_SCOPE, WEB_TOOLS, messages, tool_instructions
from proof_eval.harness.web_audit import audit_web

SEARCH = b"""<a class="result-link" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Flean-lang.org%2Fdoc%2Freference%2F">Lean &amp; simp</a>
<td class="result-snippet">Simplify <b>theorems</b>.</td>
<a class="result-link" href="https://example.com/a">Other result</a>"""


@pytest.fixture
def fetched(monkeypatch):
    calls = []

    def fetch(url, config, timeout):
        calls.append((url, timeout))
        body = (
            SEARCH
            if urlsplit(url).hostname == "lite.duckduckgo.com"
            else (
                b"<nav>ignore menu</nav><main><h1>Simplifier</h1><p>Use <code>simp</code> to simplify.</p><script>ignore script</script></main>"
            )
        )
        return body, {
            "requested_url": url,
            "url": url,
            "http_status": 200,
            "content_type": "text/html",
            "charset": "utf-8",
            "fetched_at": now(),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "body_truncated": False,
        }

    monkeypatch.setattr(web, "_fetch", fetch)
    return calls


def test_search_decodes_urls_filters_domains_and_saves_exact_source(tmp_path, fetched):
    result = web.retrieve(
        web.freeze(),
        {
            "op": "web_search",
            "query": "simp Lean",
            "domains": ["lean-lang.org"],
            "limit": 1,
        },
        tmp_path,
        1,
        remaining_seconds=4,
    )
    assert result["count"] == 1
    assert result["matches"] == [
        {
            "url": "https://lean-lang.org/doc/reference/",
            "title": "Lean & simp",
            "snippet": "Simplify theorems.",
        }
    ]
    assert "site:lean-lang.org" in parse_qs(urlsplit(fetched[0][0]).query)["q"][0]
    assert fetched[0][1] == 4
    assert (tmp_path / result["source"]["body_path"]).read_bytes() == SEARCH


def test_open_bounds_text_and_omits_scripts_navigation(tmp_path, fetched):
    result = web.retrieve(
        web.freeze(),
        {
            "op": "web_open",
            "url": "https://lean-lang.org/doc/",
            "start": 2,
            "end": 2,
        },
        tmp_path,
        1,
    )
    assert result["total_lines"] == 2
    assert result["text"] == "2: Use simp to simplify."
    assert "ignore" not in result["text"]


@pytest.mark.parametrize(
    "tool_request",
    [
        {"op": "web_search", "query": ""},
        {"op": "web_search", "query": "x" * 501},
        {"op": "web_search", "query": "x", "limit": True},
        {"op": "web_search", "query": "x", "limit": 11},
        {"op": "web_search", "query": "x", "domains": "lean-lang.org"},
        {"op": "web_search", "query": "x", "domains": ["https://lean-lang.org"]},
        {"op": "web_search", "query": "x", "extra": "ignored?"},
        {"op": "web_open", "url": "https://lean-lang.org", "end": 301},
        {"op": "web_open", "url": "https://lean-lang.org", "start": False},
        {"op": "unknown"},
    ],
)
def test_invalid_fields_do_not_access_network(tmp_path, fetched, tool_request):
    with pytest.raises(ValueError):
        web.retrieve(web.freeze(), tool_request, tmp_path, 1)
    assert fetched == []


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://lean-lang.org",
        "https://localhost/a",
        "https://127.0.0.1/a",
        "https://[::1]/",
        "https://10.0.0.1/",
        "https://example.local/",
        "https://user:secret@example.com/",
        "https://example.com:8443/",
    ],
)
def test_public_scope_rejects_local_and_credential_urls(url):
    with pytest.raises(ValueError):
        web._public_url(url, resolve=False)


def test_resolved_private_address_is_rejected(monkeypatch):
    monkeypatch.setattr(
        web.socket, "getaddrinfo", lambda *a: [(2, 1, 6, "", ("192.168.1.2", 443))]
    )
    with pytest.raises(ValueError, match="public hosts"):
        web._public_url("https://looks-public.example/")


def test_disabled_changed_and_expired_settings_do_not_fetch(tmp_path, fetched):
    request = {"op": "web_search", "query": "Lean"}
    for config in (
        None,
        {**web.freeze(), "search_endpoint": "https://another.example"},
    ):
        with pytest.raises(ValueError):
            web.retrieve(config, request, tmp_path, 1)
    with pytest.raises(ValueError, match="deadline"):
        web.retrieve(web.freeze(), request, tmp_path, 1, remaining_seconds=0)
    assert fetched == []


def test_web_policy_only_changes_enabled_condition(monkeypatch, tmp_path):
    packs = load_inputs()
    pack = next(iter(packs.values()))
    base = messages(pack)
    enabled = messages(pack, web_search=True)
    assert enabled[0]["content"] == base[0]["content"] + WEB_SCOPE
    assert enabled[1] == base[1]
    assert WEB_TOOLS not in tool_instructions("score_edges", semantic_search=True)
    assert WEB_TOOLS in tool_instructions(
        "score_edges", semantic_search=True, web_search=True
    )
    assert "access the network for" not in tool_instructions(
        "score_edges", web_search=True
    )
    configs = []
    monkeypatch.setattr(
        cli, "run", lambda cfg: configs.append(cfg) or {"status": "partial"}
    )
    assert (
        cli.main(
            [
                "prepare",
                "--provider",
                "lemex",
                "--web-search",
                "--output",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert configs[0].web_search is True
    assert RunConfig().web_search is True
    with pytest.raises(ValueError, match="boolean"):
        RunConfig(web_search="yes")


def test_offline_audit_detects_tampered_body_and_interrupted_request(tmp_path, fetched):
    config = web.freeze()
    request = {"op": "web_search", "query": "simp"}
    result = web.retrieve(config, request, tmp_path, 1)
    source = result["source"]
    record = {
        "number": 1,
        "config_sha256": fingerprint(config),
        "status": "completed",
        "request": request,
        "response": result,
        "body_path": source["body_path"],
        "body_sha256": source["body_sha256"],
    }
    write_jsonl(tmp_path / "web_requests.jsonl", [record])
    assert audit_web(tmp_path, config, deadline_expired=False)["retrieved"] == 1
    assert len(fetched) == 1
    (tmp_path / source["body_path"]).write_text("tampered")
    with pytest.raises(ValueError, match="bytes changed"):
        audit_web(tmp_path, config, deadline_expired=False)
    record = {
        k: v
        for k, v in record.items()
        if k not in ("response", "body_path", "body_sha256")
    }
    record["status"] = "started"
    write_jsonl(tmp_path / "web_requests.jsonl", [record])
    assert audit_web(tmp_path, config, deadline_expired=True)["interrupted"] == 1
    with pytest.raises(ValueError, match="deadline stop"):
        audit_web(tmp_path, config, deadline_expired=False)
    with pytest.raises(ValueError, match="without web tools"):
        audit_web(tmp_path, None, deadline_expired=True)
