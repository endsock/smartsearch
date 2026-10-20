# Smart Search promo film

Code-rendered promo film for Smart Search. Every page draws one frame per call to
`window.render(t)`; `tools/render.mjs` captures the frames with Playwright and encodes them
with ffmpeg. Nothing here is published to npm.

Current stage: three proposals with previews, see [proposals/PLANS.md](proposals/PLANS.md).

## Render

Requires Node.js 18+, ffmpeg on `PATH` and a Playwright Chromium
(`npx playwright install chromium` if you do not have one).

```sh
cd promo
npm install
node tools/render.mjs proposals/plan-a/index.html out/previews/plan-a.mp4 --fps 60 --duration 5.4
node tools/render.mjs proposals/plan-b/index.html out/previews/plan-b.mp4 --fps 30 --duration 4.8
node tools/render.mjs proposals/plan-c/index.html out/previews/plan-c.mp4 --fps 60 --duration 4.2
node tools/render.mjs proposals/plan-b/index.html out/b.png --still 4.3
```

`--size 960x540` renders a draft; `--subframes 4` adds motion blur; `--audio mix.wav` muxes sound.

## Layout

| Path | Contents |
| --- | --- |
| `shared/clawd.js` | Clawd as an 18x10 pixel grid: poses, magnifier prop, icons; Canvas and SVG output |
| `shared/motion.js` | Time-only easing, closed-form springs, seeded random, font preloading |
| `tools/render.mjs` | Frame-by-frame renderer (still, video, segment, motion blur, audio mux) |
| `proposals/` | The three plans, their preview pages and key frames |
| `assets/` | A 256 px copy of the Smart Search icon |

## Credits

- Clawd is Anthropic's mascot. This is an unofficial fan depiction, not affiliated with or endorsed by Anthropic.
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
