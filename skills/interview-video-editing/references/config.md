# 项目配置

复制assets/project.example.json到新项目工作区再填写，不修改已安装skill中的示例。示例内容不是事实，不直接用于客户发布。

## 顶层字段

- version：固定1。
- design：可选，仅填写要覆盖的字段；与assets/defaults.json深度合并。统一更换colors.gradient三个色值，而不是逐组件改色。字体字号用type对象覆盖。
- media：稳定ID到素材的映射。path相对配置文件目录解析，也可以为绝对路径；仅本地文件，无联网下载。
- scenes：按播放顺序排列，生成器自动累计开始时间，不手工维护第二条时间线。
- audio：可选音乐/音效轨，每条media、start、duration、volume。默认无音乐无音效，必须明确选用后填写。

## 媒体

kind为video/audio/image。音视频可填in、out（源秒数）和speed（0.5—2），范围必须落在原文件内。输出时长=(out-in)/speed，配置字幕使用剪辑后局部时间。速度变更时必须重做字幕对齐。

每个采用区间使用独立media ID；生成器会裁切、同步变速、转码为可渲染资产。保留原素材只读。不进行自动降噪、自动响度修复、自动气口检测或转写；这些在粗剪阶段完成。

quote与answer所用媒体必须有音轨，长度不得短于场景。预处理没有音轨的业务证据允许静音展示。

人物输入建议为871×1098画布上的透明PNG或纯黑合成图，人物右下锚定，保持原人体比例、留好标题区域。先在画布中排版，不能把任意纵横比人物直接拉伸。白色描边优先预合成于同一人物画布；可选outline={viewBox,paths}用于独立SVG描边，必须与该图使用同一坐标系。绝不复制参考嘉宾的轮廓用于另一个人。

## 文本表达

普通文本用字符串。局部强调用数组，如：

```json
[{"text":"把经验变成"},{"text":"AI系统","accent":true}]
```

文本会转义，不能填HTML/CSS。配置不执行任意脚本。两行标题分别配置，主题按全体字数均匀分配1.5秒逐字动画；无需自己给每字打时间码。

## 场景类型

- quote：media、duration、lines（1—2行）、可选kicker/top/align/objectPosition/volume。variant可选standard/compact/impact/climax/risk。risk改用两组rows={label,value}。climax为黑底；有原声时仍须指定media。金句时间依照真正剪好的原声填写。
- theme：portrait、name、role、title（两行）、topics（三组，每组1—2行），可选outline。默认时长0.04+1.5+1.5+3=6.04秒；最后气泡完成即进入后续Q。
- question：number、label、context、lines（完整问题分两行）、可选chapter/fromTopic/hold。fromTopic仅用于紧接theme的Q，取0/1/2；后续Q无需重播人物页。chapter相同的Q不允许重复。默认时长1+0.4+2×0.45+0.3=2.6秒。hold只延长最后完整问题停留。
- answer：media、duration、headline（两行）、captions、可选chapter/evidence/objectPosition/volume。多个同章answer可连续排列，无需中间加Q。人物声轨连续靠准确切点保证，不靠机械交叉淡化掩盖。
- outro：duration、lines（两行），复用主题字体与渐变，不新增旁白。

answer.captions：start/end/text，时间相对该回答开始，必须递增不重叠、不越界，与实际原声一致。
answer.evidence：media/evidenceId/start/end，在原声不断的情况下覆盖中部人物画面，保留顶部观点和底部字幕；image/video均可，视频始终静音。录屏默认contain，先准备可读的关键区域。

## 当前边界

渲染器固定1080×1440、30fps。其他画幅不能只改frame数字，需适配renderer布局。正文品牌位、复杂流程动画及额外分屏按需要扩展工程，并保持相同令牌；这些不是生成器已自动实现的功能。

只修改配置时生成新构建目录，不覆盖已有输出。project.json引用已准备的内部媒体，可再次构建；source-map.json保留原始路径供追溯，不是发布素材，分享前注意路径和资料敏感性。
