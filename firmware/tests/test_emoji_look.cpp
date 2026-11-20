// What a pure-emoji board puts on screen for a given model, and in what order the model's
// signals win. The order is the promise: link -> her own wake cue -> a question waiting
// -> a finished turn -> the reply's own mood -> her own playback -> a named face
// -> the screen. A regression here is invisible in a screenshot until the wrong face is on
// the glass at the wrong moment, so it is pinned here.
#include <cstdint>

#include "check.hpp"
#include "hg/ui.hpp"

using hg::emoji::Look;
using hg::Link;
using hg::Screen;
using hg::UiModel;

namespace {

UiModel model(Screen screen = Screen::Ready, Link link = Link::Online) {
  UiModel m;
  m.emoji = true;
  m.screen = screen;
  m.link = link;
  return m;
}

}  // namespace

TEST("emoji look: the link is the face, whatever the host named") {
  UiModel m = model(Screen::Ready, Link::Offline);
  m.look = Look::Loving;
  m.look_set = true;
  m.wake_cue = true;
  CHECK(hg::emoji_look(m) == Look::Disconnected);

  m.link = Link::Connecting;
  CHECK(hg::emoji_look(m) == Look::Connecting);
  // A network that answers but has no session yet is still "connecting", not "off line".
  m.link = Link::Network;
  CHECK(hg::emoji_look(m) == Look::Connecting);
}

TEST("emoji look: the wake cue outranks the speaking mouth") {
  UiModel m = model(Screen::Responding);
  m.speaking = true;
  m.wake_cue = true;
  CHECK(hg::emoji_look(m) == Look::Happy);  // she waves the maracas, not opens the talking mouth

  m.wake_cue = false;
  CHECK(hg::emoji_look(m) == Look::Speaking);
}

// The whole priority chain, driven directly: link -> wake -> reminder -> done ->
// mood -> Speaking -> named look -> screen.
TEST("emoji look: a reply mood beats Speaking, a reminder beats both") {
  UiModel m = model(Screen::Responding);
  m.speaking = true;
  // The wake cue is a greeting (Happy), not a reply.
  m.wake_cue = true;
  CHECK(hg::emoji_look(m) == Look::Happy);
  m.wake_cue = false;
  // A reply mood wears its own face while the reply is spoken.
  m.mood_set = true;
  m.mood = Look::Laughing;
  CHECK(hg::emoji_look(m) == Look::Laughing);
  // A blocking reminder beats the mood: the user has to act on it.
  m.screen = Screen::Prompt;
  CHECK(hg::emoji_look(m) == Look::Silly);
  m.screen = Screen::Choice;
  CHECK(hg::emoji_look(m) == Look::Shocked);
  m.screen = Screen::Responding;
  // A finished timer/task is Excited now, not Happy — and it beats the mood too.
  m.done_cue = true;
  CHECK(hg::emoji_look(m) == Look::Excited);
  m.done_cue = false;
  m.mood_set = false;
  // Without a mood, Speaking still wins over a named look, and the named look
  // shows once the playback stops.
  m.look_set = true;
  m.look = Look::Happy;
  CHECK(hg::emoji_look(m) == Look::Speaking);
  m.speaking = false;
  CHECK(hg::emoji_look(m) == Look::Happy);
  // No mood means no mood face: the screen's own face comes back.
  m.look_set = false;
  CHECK(hg::emoji_look(m) == Look::Neutral);
}

TEST("emoji look: a question waiting outranks the host's named face") {
  UiModel m = model(Screen::Prompt);
  m.look = Look::Cool;
  m.look_set = true;
  CHECK(hg::emoji_look(m) == Look::Silly);  // "?" — approval is waiting

  m.screen = Screen::Choice;
  CHECK(hg::emoji_look(m) == Look::Shocked);  // "!!" — the host needs a choice
}

TEST("emoji look: a finished turn is excited before the resting face comes back") {
  UiModel m = model(Screen::Ready);
  m.done_cue = true;
  CHECK(hg::emoji_look(m) == Look::Excited);

  // A named face for the next turn does not displace the cue: the cue is the
  // board's own state, so it goes first until it ends.
  m.look = Look::Bored;
  m.look_set = true;
  CHECK(hg::emoji_look(m) == Look::Excited);  // the cue is the board's own state: it goes first
  m.done_cue = false;
  CHECK(hg::emoji_look(m) == Look::Bored);
}

TEST("emoji look: the named face outranks the screen") {
  UiModel m = model(Screen::Thinking);
  CHECK(hg::emoji_look(m) == Look::Thinking);

  m.look = Look::Laughing;
  m.look_set = true;
  CHECK(hg::emoji_look(m) == Look::Laughing);

  // look_set with Neutral is still a named face: it clears whatever the screen would show.
  m.look = Look::Neutral;
  CHECK(hg::emoji_look(m) == Look::Neutral);
  m.look_set = false;
  CHECK(hg::emoji_look(m) == Look::Thinking);
}

TEST("emoji look: every screen with its own face, and the rest falls back to the resting face") {
  CHECK(hg::emoji_look(model(Screen::Listening)) == Look::Listening);
  CHECK(hg::emoji_look(model(Screen::Thinking)) == Look::Thinking);
  CHECK(hg::emoji_look(model(Screen::Responding)) == Look::Neutral);  // not speaking yet
  CHECK(hg::emoji_look(model(Screen::Error)) == Look::Sad);
  CHECK(hg::emoji_look(model(Screen::Updating)) == Look::Thinking);
  CHECK(hg::emoji_look(model(Screen::Alarm)) == Look::Excited);
  // A card, a dashboard, the clock: none of them has a face of its own on this board.
  CHECK(hg::emoji_look(model(Screen::Card)) == Look::Neutral);
  CHECK(hg::emoji_look(model(Screen::Clock)) == Look::Neutral);
}

TEST("emoji animation: a still face stops repainting, a moving one does not") {
  UiModel m = model(Screen::Ready);
  const uint32_t a = hg::emoji_anim_key(m);
  m.frame += 1;
  const uint32_t b = hg::emoji_anim_key(m);
  CHECK(a != b);  // the resting face glances around, so every step is a repaint

  // Thinking moves in steps of three frames, so a single frame can leave it unchanged.
  UiModel t = model(Screen::Thinking);
  const uint32_t t0 = hg::emoji_anim_key(t);
  t.frame += 1;
  CHECK(hg::emoji_anim_key(t) == t0);
  t.frame += 2;
  CHECK(hg::emoji_anim_key(t) != t0);

  // The speaking face is a fixed 20-frame wave: the mic level does not move it
  // (draw_speaking_bars ignores the level — her own voice would be the only level
  // on the board), so a level change leaves the key alone and a frame step moves it.
  UiModel s = model(Screen::Responding);
  s.speaking = true;
  const uint32_t s0 = hg::emoji_anim_key(s);
  s.level = 60;
  CHECK(hg::emoji_anim_key(s) == s0);
  s.frame += 1;
  CHECK(hg::emoji_anim_key(s) != s0);
}
