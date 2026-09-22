# 其他AI直接使用方法

## 一次性启动指令

把下面内容交给具备Git和Python执行能力的AI：

```text
通过以下公开仓库执行AI视频动作导演流程：
https://github.com/wufanw348-lgtm/ai-video-director-rc2

先克隆main分支并按README规定顺序读取V1.1-RC2。不得立即生成成品Prompt。

执行规则：
1. 用户只提供剧情、资产、目标模型、时长、必须保留内容和可选想法，不要求用户填写JSON。
2. 把自然语言输入整理成RC2任务包。
3. 原文动作过薄时，先给用户一个简短扩写确认；状态为PENDING_USER时停止。
4. 建立世界状态账本、攻防交互时间线、空间调度和战术情绪递进。
5. 防守必须在接触前开始；双方必须在同一时间、同一位置完成指定接触；力量和环境反馈不得早于接触。
6. 方案生成与反方审查必须使用不同会话或独立上下文。
7. 必须实际运行python3 tools/rc2_pipeline.py validate <任务目录>。
8. 只有返回PASS后才允许运行compile并输出最终Prompt。
9. 返回BLOCKED时不得建议“先生成试试”，只向用户展示必须由其决定的事项。
```

## 用户提交格式

```text
【剧情】
粘贴小说、剧本或动作段。

【资产】
标准名称｜类型｜状态｜参考文件

【模型与单条时长】
模型：
时长：

【必须保留】
没有就写“无”。

【特别偏好】
没有就写“无，由系统决定”。
```

## 命令

```bash
git clone https://github.com/wufanw348-lgtm/ai-video-director-rc2.git
cd ai-video-director-rc2
python3 tools/rc2_pipeline.py init work/my_project
```

AI完成任务包后：

```bash
python3 tools/rc2_pipeline.py validate work/my_project
```

通过后：

```bash
python3 tools/rc2_pipeline.py compile work/my_project
```

最终文件：

```text
work/my_project/12_final_prompt.md
```

## 重要限制

如果目标AI无法运行Git和Python，只能把本仓库当作规则参考，不能声称已经通过RC2门禁。
