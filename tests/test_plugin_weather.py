"""The weather tool, at the plugin's edge.

The fork keeps ``weather.py`` (QWeather) but upstream 0.6 shipped without the tool that calls it,
so the model fell back to searching the web for forecasts. These tests pin the tool's contract:
it answers by voice, it never puts a card on a board that draws no text, and it is registered
with the key/host check rather than the hub check (a forecast is worth saying with no gadget).
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
        self.cards = []

    async def show_card(self, title, body, ttl_s=15, **_kw):
        self.cards.append((title, body))
        return True


@pytest.fixture
def tools_with(monkeypatch):
    from hermes_gadget_plugin import tools

    def install(session):
        monkeypatch.setattr(tools, "_adapter", lambda: object())
        monkeypatch.setattr(tools, "_resolve", lambda _adapter, _ref: (session, None))
        monkeypatch.setattr(tools, "_usable", lambda _session: None)
        monkeypatch.setattr(tools, "_run", lambda _adapter, coro, timeout=None: asyncio.run(coro))
        return tools

    return install


@pytest.fixture
def quiet_weather(monkeypatch):
    """weather.answer/card without a network call; the module itself is covered elsewhere."""
    from hermes_gadget_plugin import weather

    monkeypatch.setattr(weather, "answer", lambda days=3, place=None: f"扬州 晴 10℃，{days} 天预报")
    monkeypatch.setattr(weather, "card", lambda days=3, place=None: ("扬州天气", "晴 10℃"))


def test_the_weather_tool_speaks_the_forecast(tools_with, quiet_weather):
    tools = tools_with(_FakeSession())
    out = json.loads(tools.gadget_weather({"days": 2}))
    assert out["success"] is True
    assert "扬州" in out["answer"]
    assert "shown_on" not in out  # show was not asked for


def test_a_textless_board_gets_the_forecast_spoken_not_drawn(tools_with, quiet_weather):
    session = _FakeSession(face="emoji")
    tools = tools_with(session)
    out = json.loads(tools.gadget_weather({"show": True}))
    assert out["success"] is True and out["answer"]
    assert session.cards == []  # nothing was drawn on a board with no text
    assert "spoken" in out["shown_error"]


def test_a_text_board_still_gets_the_card(tools_with, quiet_weather):
    session = _FakeSession(face="mascot")
    tools = tools_with(session)
    out = json.loads(tools.gadget_weather({"show": True}))
    assert out["shown_on"] == session.name
    assert session.cards == [("扬州天气", "晴 10℃")]


def test_the_weather_tool_is_registered_with_the_key_check():
    """Without this registration the model has no weather tool and searches the web instead."""
    from hermes_gadget_plugin import tools

    registered = {}

    class _Ctx:
        def register_tool(self, *, name, toolset, schema, handler, check_fn, description, emoji):
            registered[name] = check_fn

    tools.register_tools(_Ctx())
    assert "gadget_weather" in registered
    assert registered["gadget_weather"] is tools.weather_available
    # The device tools keep the hub check; weather must not be gated on a connected board.
    assert registered["gadget_face"] is tools.available


def test_weather_availability_follows_the_key_and_host(monkeypatch):
    from hermes_gadget_plugin import weather, tools

    monkeypatch.setattr(weather, "config", lambda: {"host": "x", "key": "y"})
    assert tools.weather_available() is True

    def _missing():
        raise weather.WeatherError("QWEATHER_KEY is not set")

    monkeypatch.setattr(weather, "config", _missing)
    assert tools.weather_available() is False
