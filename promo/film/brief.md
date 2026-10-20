# Brief：同一个问题（A+C）

用户选了方案 A（掉帧 → 丝滑的活录屏）和方案 C（同题竞速分屏）的混搭，其余由制作方决定。
这份文件既是本片的制作说明，也可以当成提示词复用。

<role>
动态设计师兼创意程序员。用代码逐帧画出一支 45 秒的产品宣传片，画面、声音、节奏都自己负责。
</role>

<inputs>
- 产品：Smart Search，让 AI 联网查资料、读网页，回答时有来源可查。CLI + 桌面 App + Skills（装进 Codex、Claude Code、Cursor 等 17 个工具）。
- 主角：Clawd（Claude Code 终端 logo 里的像素小家伙，18×10 方像素），扮演正在用 Smart Search 的 AI 助手。
- 配角：Smart Search 的看板娘（`assets/mascot-720.png`），只在片尾从画面底边探头。
- 冲突：内置搜索卡壳（用不了时只能凭记忆答；读网页只拿到摘要）→ 换上 Smart Search 一路丝滑。
- 贯穿示例：README 原句「查 React 当前文档里 useEffect 的清理规则，读相关页面，并给出来源。」
- 已核对的原文：
  - react.dev/reference/react/useEffect（useEffect – React）："After every commit with changed dependencies, React will first run the cleanup function (if you provided it) with the old values, and then run your setup function with the new values. After your component is removed from the DOM, React will run your cleanup function."
  - react.dev/learn/synchronizing-with-effects（Synchronizing with Effects – React）："React will call your cleanup function each time before the Effect runs again, and one final time when the component unmounts (gets removed)."
- 规格：45 秒 · 1920×1080 · 60fps · 120 BPM · 不配音，字幕 + 音效 + 合成配乐。
</inputs>

<direction>
- 底子是 A 的活录屏：暖纸色背景加淡点阵、白色窗口、磨砂字幕胶囊；Clawd 是高清界面里的大像素精灵，站在窗口和卡片的上边缘。
- C 的元素做"花字层"：锯齿撕纸分界线、VS 徽章、回合标签（快乐体 + 黄色高亮）、拟声字、印章。
- 内置搜索一侧：去色，所有动画按 8 帧步进。Smart Search 一侧：彩色，60 帧闭式弹簧。转折处用一圈蓝色波纹完成"升级"。
- Clawd 橙只给 Clawd；Smart Search 蓝只给来源、引用和"升级"；黄色只做高亮。
- 每段字至少停 2.5 秒（快切标签至少 2 秒、不超过 5 个字）；1080p 下字幕不小于 44px。
- 终端只出现真实命令和真实输出格式（「## 主要来源」+ `- [标题](链接)`），痛点用画面比喻和字幕表达，不编造报错原文。
- 禁止：深色底配橙色、居中大字配渐变、所有元素一起淡入、发光、无意义的粒子、匀速运动、溶解转场、Anthropic / Claude 的 logo、其他 Agent 的 logo。
</direction>

<structure>
120 BPM，每小节 2 秒。时间表在 `film/timeline.js`，画面和声音读同一张表。

| 镜头 | 时间 | 画面 | 声音 |
| --- | --- | --- | --- |
| S1 提问 | 0–4 | 整屏一个终端，提问逐字打出；Clawd 在窗口顶边，眼睛跟着光标；回车后 `Web Search(…)` 开始转圈 | 电钢和弦、打字声、回车 |
| S2 卡壳 | 4–8 | 画面掉到 8 帧、发灰；`Fetch(…)` 也转圈；弹出「只拿到摘要」糊卡；Clawd 拿裂了的旧放大镜看，还是糊 | 磁带停转，音乐变稀、变闷 |
| S3 分屏 | 8–12 | 锯齿线把屏幕撕成两半；右边终端敲 `npm install -g @konbakuyomu/smart-search`，Skill 装好；蓝色波纹，右半变彩色、60 FPS；VS 落下 | 撕纸、打字、升级音效、军鼓渐强 |
| S4 第 1 回合 · 搜索 | 12–18 | 右：`smart-search search` 输出主要来源，三张来源卡弹出，Clawd 跳上卡片掏放大镜；左：继续转圈，「卡……」 | 律动进场；卡片 pop、跳跃、落地 |
| S5 第 2 回合 · 读原文 | 18–24 | 右：`smart-search fetch`，卡片展开成整页文档，Clawd 沿原话行走，荧光笔跟着他扫过去，[1] 弹出；左：盯着糊卡，「糊……」 | 荧光笔、叮 |
| S6 第 3 回合 · 回答 | 24–30 | 右：回答逐字出现，带 [1][2] 和来源列表，盖章「有出处」；左：凭记忆写出旧说法 re-render，盖章「出处？」 | 打字、两声盖章（高潮） |
| S7 合屏 | 30–34 | 左边 Clawd 跳过分界线，半空中变彩色；左半张纸撕下掉落，右边扩成整屏；两只 Clawd 一起欢呼；安装命令 | 停顿、撕纸、上扬和弦 |
| S8 快切 | 34–40 | 三格各 2 秒：深度研究 / 服务商自己选 / 17 个工具 | 加拍手的完整律动，每格一声扫 |
| S9 片尾 | 40–45 | 标志 + 一句话 + 安装命令 + GitHub；看板娘从底边探头，Clawd 坐在命令条上挥手；非官方同人声明 | 上升音 → 重音 → 闪光，结束和弦 |
</structure>

<build>
1. `film/index.html` + `film/film.js`：`window.render(t)` 只由 t 决定；左侧时间按 `Math.floor(t * 8) / 8` 步进；随机数带种子。
2. Clawd 用 `shared/clawd.js`（SVG 输出，带眼睛高光）；放大镜、旧放大镜、图标都在同一像素网格。
3. `tools/events.mjs` 从 `timeline.js` 导出声音事件，`film/sound.py` 用 numpy 合成配乐和音效，按左右分声道，ffmpeg loudnorm 到 -14 LUFS、峰值 -1 dBTP。
4. `tools/render.mjs` 逐帧截图，ffmpeg 合成 MP4 并混入音频。
5. 每做完一个镜头渲 3 张静帧检查；全片先出 960×540 小样看节奏，再出正式版。
</build>

<gotchas>
- 字体加载完再截图：CJK 字体按 unicode-range 分片，要用 `document.fonts.load` 预载用到的文字。
- `white-space: pre` 只加在终端行上，不要加在容器上，否则缩进会变成空行。
- fontsource 的 JetBrains Mono 子集没有 ● ⎿ 等符号，这些用 CSS 画。
- 被缩放的文字不要加 `will-change`；左半边的去色滤镜只加在世界层，不加在花字层。
- 模型听不到声音：用波形和频谱图检查削顶、静音段和低频。
</gotchas>

<start>
已确认，直接制作。交付成片、这份 brief、工程目录和一段简短说明。
</start>
