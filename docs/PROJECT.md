# 项目与设计（V1.3.0）

## 需求对应

| 需求 | 实现与验收入口 |
| --- | --- |
| 收藏联系人 | 星标按钮、星标筛选和统计；`PATCH /api/contacts/<id>/favorite`；`tests/test_contacts.py`。 |
| 一人多种联系方式 | `contact_methods` 一对多结构、八类方式及独立标签；新建/编辑/详情页；`tests/test_method_labels.py`。 |
| Excel 导入导出 | 主表每人一行、每类信息独立列，附加标签表；模板、预览、跳过/覆盖、往返测试；`tests/test_excel.py`、`tests/test_import_modes.py`。 |
| 界面与交互 | 中文响应式布局、搜索、排序、批量、回收站；`tests/test_frontend.py` 和浏览器冒烟。 |
| 公网演示（可选） | Gunicorn 启动配置已准备；**只有实际部署并提供可访问链接后才算完成**。 |

评分与最终提交材料须以教师发布的原始要求为准；本文件不替代课程说明。

## 架构

`app.py` 创建 Flask 应用；`addressbook/routes.py` 暴露页面和 JSON API；`validation.py` 校验请求；`repository.py` 执行 SQLite 读写；`excel.py` 处理 `.xlsx`；`templates/index.html` 与 `static/app.js`、`styles.css` 构成无构建步骤的前端。默认数据库位于 `instance/addressbook.db`。

`contacts` 保存姓名、收藏、备注、创建/更新时间和软删除时间；`contact_methods` 保存类型、内容、标签和顺序。启动时先建表，再补旧库缺失的 `label` 与 `deleted_at` 列，最后建索引。删除先进入回收站，彻底删除才级联移除联系方式。

导入预检与正式导入共用 `repository._import_decision()` 的逐行规则；预检只读，正式导入在单事务中处理。同名判断只针对未删除联系人。导入时有错误则不写任何记录。Excel 导出对可能被识别为公式的文本加安全前缀，重新导入时还原。

## 接口摘要

| 路径 | 用途 |
| --- | --- |
| `GET /api/health` | 状态、版本与统计。 |
| `/api/contacts`、`/api/contacts/<id>` | 列表、创建、详情、编辑、软删除。 |
| `PATCH /api/contacts/<id>/favorite` | 收藏状态。 |
| `/api/trash`、`/api/contacts/<id>/restore` | 回收站、恢复和清空。 |
| `POST /api/contacts/bulk` | 批量收藏、删除、恢复等。 |
| `GET /api/contacts/template`、`/api/contacts/export` | Excel 模板和按当前筛选导出。 |
| `POST /api/contacts/import/preview`、`/api/contacts/import` | 预检和正式导入；`mode=skip|overwrite`。 |

## 团队代码规范

- 功能改动先在分支提交，经搭档审查、跑完测试后再合并；不要直接覆盖 `main` 上的新版本。
- API 输入经过 `validation.py`；数据库值使用参数化 SQL；动态排序和批量动作只用白名单。
- 修改功能时同步补测试和文档；网页文本用转义函数后再插入 HTML；不要提交真实通讯录数据库。
- 版本号以 `/api/health`、页脚、README 和本文件一致为准。

## 边界

这是无账号体系的课程演示应用。公网 URL 上任何访问者都可能修改演示数据，不适合保存真实个人资料。Render 免费服务的本地 SQLite 数据不会长期保留；持久保存需要额外的付费磁盘或另行迁移到持久数据库。
