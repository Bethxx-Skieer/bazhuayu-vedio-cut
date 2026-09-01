# 项目生命周期与状态闸门（子 Skill）

从主总控下沉的状态机细则。字段与校验规则见 [project-manifest.md](project-manifest.md)；各阶段产物规范见 01–06 阶段文档。

## 状态链（固定顺序，不允许跳级）

```text
initialized
→ evidence_ready
→ script_locked
→ voice_style_locked
→ voice_generated
→ subtitle_timeline_locked
→ visual_timeline_locked
→ preview_approved
→ variants_rendered
→ qa_passed
→ delivered
```

## 状态 → 必备产物 → 进阶条件

| 当前状态 | 必须存在的产物 | 才能进入下一阶段 |
|---|---|---|
| `initialized` | 项目目标、输入目录、输出目标 | 原始资料可访问 |
| `evidence_ready` | 素材证据库、可用区间、缺口清单 | 事实和画面边界清楚 |
| `script_locked` | 唯一旁白、自然句 ID、目标时长 | 用户确认文案与节奏 |
| `voice_style_locked` | 音色、语速、特殊词和停顿试听 | 用户确认声音样本 |
| `voice_generated` | 完整配音、逐句实际时长、配音报告 | 无错读、截字和异常加速 |
| `subtitle_timeline_locked` | 唯一 SRT/JSON、一致性报告 | 字幕拼接文字等于旁白 |
| `visual_timeline_locked` | 唯一镜头表、素材或组件映射 | 每句有画面且关键任务闭环 |
| `preview_approved` | 前60秒预览、跨章节关键帧 | 音画、字体、裁剪和状态通过 |
| `variants_rendered` | 横版与所需平台版本 | 所有版本引用同一内容时间线 |
| `qa_passed` | 内容、声音、字幕、画面和技术报告 | 所有校验为 `ok` |
| `delivered` | 完整、干净的最终交付包 | 七个交付目录均只含当前最终版本 |

## 推进与回退规则

1. 只有对应产物和审批存在时才更新状态；每次推进前运行 `python scripts/validate_project_manifest.py project-manifest.json`，校验失败立即停止并修复，不得手工跳过失败项。
2. 用户要求回退文案或声音时，把状态回退到最早受影响阶段，并只重新生成该阶段及其下游产物；不从原始素材全部重来。
3. 目标时长只用于规划；`voice_generated` 之后的一切时间以实际配音时长为准。
4. 状态与产物的对应关系、ID 体系和清单字段见 [project-manifest.md](project-manifest.md)。
