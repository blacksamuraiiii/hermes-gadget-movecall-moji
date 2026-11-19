"""The face tool and the textless board, at the plugin's edge.

A pure-emoji board advertises ``caps.face: "emoji"`` and no card, choice, dashboard or
profiles cap, because its screen carries no text at all. These tests pin both halves of that
contract: the card tools refuse instead of pretending to have shown something, and
``gadget_face`` names a face through the ``emote`` message.
"""

from __future__ import annotations

import asyncio
import json

import pytest


class _FakeSession:
    name = "Moji"
    device_id = "hg-0000000000000000"
    charset = "utf-8"
    paired = True

    display = {"text_cols": 24}
    card_items = 12
    card_qr_bytes = 64

    def __init__(self, face="emoji"):
        self.face = face
        self.emotes = []
        self.notices = []

    async def send_notice(self, text, ttl_s=8):
        self.notices.append(text)

    def card_shown_as(self, **_kw):
        return "card"

    async def emote(self, look, ttl_s=8):
        self.emotes.append((look, ttl_s))


@pytest.fixture
def tools_with(monkeypatch):
    """The tools module with one fake session behind it."""
    from hermes_gadget_plugin import tools

    def install(session):
        monkeypatch.setattr(tools, "_adapter", lambda: object())
        monkeypatch.setattr(tools, "_resolve", lambda _adapter, _ref: (session, None))
        monkeypatch.setattr(tools, "_usable", lambda _session: None)
        monkeypatch.setattr(tools, "_run", lambda _adapter, coro, timeout=None: asyncio.run(coro))
        return tools

    return install


@pytest.mark.parametrize("tool, args", [
    ("gadget_display", {"text": "the pasta is ready"}),
    ("gadget_ask", {"question": "Which one?", "options": ["Pasta", "Rice"]}),
    ("gadget_interpret", {"languages": ["English", "Chinese"]}),
])
def test_a_pure_emoji_board_refuses_everything_that_needs_text(tools_with, tool, args):
    session = _FakeSession()
    tools = tools_with(session)
    out = json.loads(getattr(tools, tool)(args))
    assert out["success"] is False
    # The model is told what to do instead, not just that it failed.
    assert "spoken" in out["error"] and "gadget_face" in out["error"]


def test_a_text_board_keeps_its_card_tools(tools_with):
    from hermes_gadget_plugin import tools

    session = _FakeSession(face="mascot")
    tools_with(session)

    async def card(*_a, **_k):
        return True

    sent = []

    async def show_card(title, body, ttl_s=15, **_kw):
        sent.append((title, body))
        return True

    session.show_card = show_card
    out = json.loads(tools.gadget_display({"text": "the pasta is ready"}))
    assert out["success"] is True
    assert sent == [("", "the pasta is ready")]


def test_the_face_tool_names_a_face_by_emote(tools_with):
    session = _FakeSession()
    tools = tools_with(session)
    out = json.loads(tools.gadget_face({"look": "loving", "seconds": 3}))
    assert out["success"] is True
    assert session.emotes == [("loving", 3.0)]
    assert "not_shown" not in out  # the board draws it


def test_the_face_tool_says_so_when_a_text_board_ignores_it(tools_with):
    session = _FakeSession(face="mascot")
    tools = tools_with(session)
    out = json.loads(tools.gadget_face({"look": "loving"}))
    # It went out, and the answer does not claim the user saw anything.
    assert out["success"] is True
    assert "not_shown" in out


def test_the_face_tool_clamps_a_missing_or_nonsense_duration(tools_with):
    session = _FakeSession()
    tools = tools_with(session)
    tools.gadget_face({"look": "hi"})
    tools.gadget_face({"look": "hi", "seconds": 0})
    tools.gadget_face({"look": "hi", "seconds": "soon"})
    assert [ttl for _, ttl in session.emotes] == [8.0, 8.0, 8.0]
