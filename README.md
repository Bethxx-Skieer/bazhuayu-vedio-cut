# bazhuayu-vedio-cut

团队视频剪辑工作仓库：沉淀「教程 / 社媒宣发 / 企业业务演示」视频剪辑技能包、项目工程与规范，配合千问办公（QwenWork）使用。

## 目录结构

```text
bazhuayu-vedio-cut/
├── README.md
├── .gitignore
├── skills/
│   └── tutorial-video-slicing-workflow/   # 视频剪辑技能组（主调度 + 子Skill + 脚本 + 素材）
│       ├── SKILL.md                       # 主文档：只做场景路由与全局闸门（≤100行）
│       ├── .skill-metadata.yaml           # 千问办公推荐查询（7 个能力各一条）
│       ├── references/                    # 9 个子 Skill 文档，按需完整读取
│       ├── scripts/                       # 字幕烧录、配音、音效合成、质检闸门等脚本
│       └── assets/                        # 字幕/画布/音色样式配置、音效库、示例 cue 表
├── projects/
│   ├── _template/                         # 新建剪辑项目的模板
│   └── <项目名>/                          # 每个剪辑项目一个文件夹
└── work/                                  # 临时处理区（解压、截图、中间产物），不入库
```

## 技能安装（团队成员每人一次）

1. 安装并登录 [千问办公](https://qwenwork.cn)，或直接把技能包目录拷贝到本机技能目录：

```text
Windows:  %USERPROFILE%\.qwenworkcn\skills\tutorial-video-slicing-workflow\
macOS:    ~/.qwenworkcn/skills/tutorial-video-slicing-workflow/
```

2. 拷贝的就是本仓库 `skills/tutorial-video-slicing-workflow/` 整个目录，重启千问办公后自动生效。
3. 环境要求：Python 3.12+，首次执行时按技能文档安装 `imageio-ffmpeg`（自带 ffmpeg，无需系统安装）。

## 使用方式

在千问办公新会话中附上素材并说明模式即可触发技能，例如：

- 教程切片：`按板块切割这份教程并提取高光切片，输出到 projects/xxx/deliverables/`
- 企业业务演示：`用这些真实操作素材和业务稿制作 Agent/RPA 业务演示视频，先锁脚本给我确认`
- 社媒宣发：`把这段无字幕演示素材剪成效果前置宣发片，先出时间线方案`
- 字幕 / 配音 / 小红书 3:4：参考技能卡片中的推荐查询。

主 `SKILL.md` 会按诉求路由到 `references/` 下的子 Skill；所有模式共享五条全局硬闸门（先锁脚本、整句配音、真实素材优先、统一代码渲染单一时间源、双重预览 + `validate_render_lock.py` 交付闸门）。

## 项目协作规范

- 每个剪辑任务在 `projects/` 下建独立文件夹，命名 `日期-题材`，如 `20260828-mcp教程切片`；从 `projects/_template/` 复制起步。
- 视频、音频、截图等大文件一律不提交（见 `.gitignore`）；素材走网盘/共享目录，仓库里只保留脚本、cue 表、时间轴、配置和说明文档。
- 成品交付结构遵循技能文档约定（教程切片用 `01_板块切割/02_横版切片/03_小红书3比4`；企业业务演示用 `01_正式视频`–`07_工程`）。
- 修改剪辑规范时直接改 `skills/tutorial-video-slicing-workflow/` 并提 PR，合并后成员 `git pull` 重新拷贝技能目录即可全员生效。

## 更新流程

```bash
git pull
# 然后把 skills/tutorial-video-slicing-workflow 覆盖拷贝到本机 ~/.qwenworkcn/skills/
```
