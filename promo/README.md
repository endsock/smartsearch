# Smart Search promo film

Code-rendered promo film for Smart Search. Every page draws one frame per call to
`window.render(t)`; `tools/render.mjs` captures the frames with Playwright and encodes them
with ffmpeg. Nothing here is published to npm.

The film is **同一个问题** (45 s, 1920×1080, 60 fps): the same question asked twice, first with the
built-in search (grey, 8 fps), then side by side with Smart Search (colour, 60 fps), until the two
halves merge. The plan is in [film/brief.md](film/brief.md); the earlier three proposals are in
[proposals/PLANS.md](proposals/PLANS.md).

## Build

Requires Node.js 18+, Python 3 with numpy and scipy, ffmpeg on `PATH` and a Playwright Chromium
(`npx playwright install chromium` if you do not have one).

```sh
cd promo
npm install
bash film/build.sh          # out/film/smart-search-promo.mp4, about 15 minutes
bash film/build.sh draft    # out/film/draft.mp4, 960x540 @ 30 fps
node tools/render.mjs film/index.html out/still.png --still 20.5
```

`film/timeline.js` is the one timetable: the picture reads it, and `tools/events.mjs` exports its sound
cues for `film/sound.py`, which synthesizes the score and effects. The build peak-limits the mix and
normalises it to -14 LUFS / -1 dBTP before muxing.

Preview pages for the proposals render the same way:

```sh
node tools/render.mjs proposals/plan-a/index.html out/previews/plan-a.mp4 --fps 60 --duration 5.4
node tools/render.mjs proposals/plan-b/index.html out/previews/plan-b.mp4 --fps 30 --duration 4.8
node tools/render.mjs proposals/plan-c/index.html out/previews/plan-c.mp4 --fps 60 --duration 4.2
```

`--size 960x540` renders a draft; `--subframes 4` adds motion blur; `--audio mix.wav` muxes sound.

## Layout

| Path | Contents |
| --- | --- |
| `film/` | The film: brief, timetable, page, render logic, sound synthesis, build script, review notes |
| `shared/clawd.js` | Clawd as an 18x10 pixel grid: poses, magnifier props, icons; Canvas and SVG output |
| `shared/motion.js` | Time-only easing, closed-form springs, seeded random, font preloading |
| `tools/render.mjs` | Frame-by-frame renderer (still, video, segment, motion blur, audio mux) |
| `tools/events.mjs` | Exports a timetable's sound cues to JSON |
| `proposals/` | The three plans, their preview pages and key frames |
| `assets/` | Smaller copies of the Smart Search icon and the app mascot |

## Credits

- Clawd is Anthropic's mascot. This is an unofficial fan depiction, not affiliated with or endorsed by Anthropic.
- `assets/smart-search-256.png` and `assets/mascot-720.png` are resized copies of Smart Search's own artwork
  (`assets/branding/smart-search.png`, `desktop/windows/Assets/mascot.png`).
- Quoted documentation: react.dev `useEffect` reference and "Synchronizing with Effects", checked on 2026-10-20.
- Score and sound effects are synthesized in `film/sound.py`; no samples are used.
- Fonts (SIL Open Font License 1.1, via Fontsource): Fusion Pixel 12px, Noto Sans SC, ZCOOL KuaiLe, Inter, JetBrains Mono.
- `tools/render.mjs` is a Node port of `scripts/render.py` from [Kianzzz/xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video).
- The Clawd grid follows the derivation in [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar).

Both projects are MIT licensed:

```text
Copyright (c) 2026 周行 (Kianzzz)
Copyright (c) 2026 LemoLab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
