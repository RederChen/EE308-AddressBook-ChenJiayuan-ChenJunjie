# 版本记录

| 版本 | 负责人 | 可核对的主要变化 |
| --- | --- | --- |
| V1.0 | Chen Junjie | 初始联系人 CRUD、收藏、多联系方式、Excel 导入导出与测试。 |
| V1.1 | Chen Jiayuan | 中文界面、每条联系方式的独立标签、标签 Excel 工作表、旧库迁移。 |
| V1.2 | Chen Junjie | 回收站、批量操作、排序分页、按筛选导出、导入预检与覆盖策略，以及安全和错误处理修复。 |
| **V1.3.0** | Chen Jiayuan | 导入预览与实际处理策略统一；换文件/策略必须重新预览；跳过数量准确回报；版本与中文界面测试统一；支持可配置 SQLite 路径、Gunicorn/Render 启动；精简并更新交付文档。 |

V1.3 未改变 Excel 主表的 11 列结构，也未改变现有联系人 API 的主要字段。导入预览响应增加 `mode`，其中 `create`、`update`、`skip` 表示按选定策略逐行计算的实际动作；正式导入响应增加 `skipped_count`，原有 `skipped` 姓名样例仍保留（最多 50 条）。

## GitHub 迭代证据

- [V1.1 PR #1](https://github.com/RederChen/EE308-AddressBook-ChenJiayuan-ChenJunjie/pull/1)
- [V1.0 补传 PR #2](https://github.com/RederChen/EE308-AddressBook-ChenJiayuan-ChenJunjie/pull/2)：其合并发生在 V1.1 之后，曾覆盖部分升级源码；保留历史，不改写 PR 编号。
- [V1.2 PR #3](https://github.com/RederChen/EE308-AddressBook-ChenJiayuan-ChenJunjie/pull/3)：把升级后的完整源码重新接回 `main`。
- V1.3 PR：**待本人上传后补链接**；本压缩包不是 Git 提交记录。

本文件只陈述可在现有源码和 Git 历史中核对的变化。博客、视频、云部署及个人工时要在实际完成后另行补证据。
