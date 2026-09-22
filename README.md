# AI Video Director RC2

面向AI视频动作场景的可执行导演门禁。它不保存具体小说、角色或成品Prompt，而是要求AI在生成前完成动作扩写确认、世界状态、攻防同步、空间调度、战术情绪递进、失败匹配和独立反方审查。

当前版本：`1.1.0-rc.2`。这是公开测试候选版，不是V1.1正式稳定版。

## 免鉴权获取

```bash
git clone https://github.com/wufanw348-lgtm/ai-video-director-rc2.git
cd ai-video-director-rc2
```

更新：

```bash
git pull --ff-only origin main
```

Public仓库的读取、克隆和拉取不需要登录。提交、修改和发布仍需要GitHub鉴权。

## 其他AI读取顺序

1. `core/V1.1-RC2/00_VERSION_STATUS.md`
2. `core/V1.1-RC2/00_README_FIRST.md`
3. `core/V1.1-RC2/01_用户入口/给其他AI的执行指令.md`
4. `core/V1.1-RC2/02_运行规则/RC2强制流程.md`
5. `core/V1.1-RC2/03_数据模板/`
6. `core/V1.1-RC2/04_失败规则/failure_rules.json`
7. `tools/rc2_pipeline.py`

## 最短运行方法

```bash
python3 tools/rc2_pipeline.py init work/my_project
python3 tools/rc2_pipeline.py validate work/my_project
python3 tools/rc2_pipeline.py compile work/my_project
```

只有`validate`返回以下结果，才允许编译最终Prompt：

```text
PASS：允许进入Prompt编译/生成
```

缺少产物、扩写未确认、攻防不同步、接触时间或位置不一致、状态断裂、资产名漂移或反方审查未通过时，系统必须返回`BLOCKED`。

## 直接交给其他AI的启动语

见：[docs/AI_DIRECT_USE.md](docs/AI_DIRECT_USE.md)

## 当前能力边界

运行器负责确定性验证和阻断，不负责自动调用外部模型。使用环境必须能够读取仓库、创建JSON文件并运行Python。只能聊天、不能执行代码的AI无法证明门禁真正通过。
