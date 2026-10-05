from proof_eval.providers.events import parse_events


def test_success_requires_final_and_allows_tools():
    events = [
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "theorem x : True := by trivial"},
        },
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 20,
                "output_tokens": 10,
                "cached_input_tokens": 0,
            },
        },
    ]
    assert parse_events(events, events[0]["item"]["text"], 0)["status"] == "received"
    for extra in ([{"type": "turn.failed"}], [events[-1]]):
        assert (
            parse_events(events + extra, events[0]["item"]["text"], 0)["status"]
            == "transport_error"
        )
    assert (
        parse_events(
            events
            + [{"type": "item.completed", "item": {"type": "command_execution"}}],
            events[0]["item"]["text"],
            0,
        )["tool_items"]
        == 1
    )
    assert parse_events(events, "different final", 0)["status"] == "transport_error"
