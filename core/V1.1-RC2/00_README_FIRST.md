# V1.1-RC2：可执行门禁候选版

RC2用于修复RC1“有规则、无强制”的问题。它不是成品Prompt合集，而是一个失败关闭的生产流程：必要产物缺失、状态断裂、资产术语漂移或风险未解决时，系统拒绝输出最终Prompt。

## 用户只需要提供

1. 原文或剧情段；
2. 已有资产名称及参考文件；
3. 目标视频模型；
4. 单条时长；
5. 必须保留的内容（没有可写“无”）。

其他内容原则上由AI规划。只有会改变剧情、角色设定、资产设计或成本的选择才询问用户。

## 运行

```bash
python3 tools/rc2_pipeline.py init work/my_project
python3 tools/rc2_pipeline.py validate work/my_project
python3 tools/rc2_pipeline.py compile work/my_project
```

`compile`只有在全部门禁通过后才会产生`12_final_prompt.md`。

## 当前边界

运行器负责确定性检查和阻断，不负责调用外部AI。导演预检、调度规划、镜头设计与反方审查仍由上层AI分别完成，但必须写入规定的数据文件并接受运行器验证。
