# 制作与复用

## 一次新项目

1. 按workflow完成主线、证据与唯一执行脚本。复制assets中的配置和表格到项目工作区。
2. 按 [subtitle-audio-workflow.md](subtitle-audio-workflow.md) 完成原声粗剪、逐句断句、字幕校对、降噪、去采访者插话与气口、最终对时，再填写media源区间、scenes和局部字幕；不让生成器替你推断访谈逻辑。
3. 人物抠图/描边在项目内准备；样本关键帧只帮助对照，不当作新客户人像。
4. 保持默认组件，按项目替换配色、主题、人物、金句、问答、证据。修改design一次会同步CSS与SVG渐变。
5. 用本skill绝对路径执行：

```sh
node /path/to/interview-video-editing/scripts/build.mjs --validate /project/config.json
node /path/to/interview-video-editing/scripts/build.mjs /project/config.json /project/work/build-001
```

验证会检查媒体存在、源区间、音轨、时长、字幕范围、重复Q、配置类型。生成器使用FFmpeg/FFprobe；运行时缺失应报告或使用已有环境，不自动改系统配置。

6. 在生成目录运行npm run check。需要本地浏览器/服务权限时走工具审批。可用HyperFrames skill负责渲染器使用细节。
7. 检查通过后运行：

```sh
npm run render -- --quality=standard --workers=2 --output=/project/work/review.mp4
```

先样段后完整片。发布母版可使用high；不宣称自动等于视觉验收。

## 输出

- index.html、package.json：可渲染工程，锁定CLI版本。
- assets/media：裁剪/变速后的工作素材。
- project.json：自包含、可再构建的配置。
- source-map.json：原始证据与素材追溯。
- timeline.json：场景与字幕实际开始/结束。
- captions.srt：只导出正文字幕；片头强调字、Q和观点留在场景配置。
- DESIGN.md：此次解析后的唯一样式参数。

## 增量修改

- 改配色/字号：只改design，重新生成，检查最长文字和对比度。
- 改标题/身份：只改对应场景，复核适配；不改全片字幕。
- 改原声切点或速度：同时更新受影响局部字幕和证据时机，重新累计后续时间。
- 改降噪或去气口：以最终音画时间线重算受影响字幕，不沿用旧字幕时间戳；检查切点前后唇形、帧连续性与音频衔接。
- 改某个Q放大：motion.expand会更新全部Q的默认放大时长；只希望单个Q变化时先扩展显式局部覆盖，不手工改一份时间线而漏另一份。
- 新镜头：重新判断人脸与文本锚点，不能继承旧人物位置当作安全保证。
- 现有项目只做局部修改，不必迁移到此生成器；遵守当前工程结构和同一规范即可。

## 不包含的自动化

该生成器是精剪模板，不是自动编导。语义筛选、转写纠错、逐句响度、抠图、真实证据核验和看听验收由工作流完成。没有素材时不能用假内容填成“已完成”。
