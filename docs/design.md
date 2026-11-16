# 通讯录应用设计说明

## 1. 架构

采用轻量三层 Web 架构：浏览器单页界面负责交互，Flask JSON API 负责校验与业务流程，SQLite 负责持久化。OpenPyXL 仅在导入导出模块处理 `.xlsx`，与 HTTP 和 SQL 解耦。

```text
HTML / CSS / JavaScript
          │ fetch(JSON / multipart / xlsx)
          ▼
      Flask routes
      │     │     │
 validation │   excel.py
      │     │     │
      └──── repository.py ────► SQLite
```

## 2. 数据模型

`contacts` 保存联系人主体：`id`、`name`、`favorite`、`notes`、`created_at`、`updated_at`。  
`contact_methods` 保存联系方式：`id`、`contact_id`、`kind`、`label`、`value`、`sort_order`，以外键关联联系人并启用级联删除。

一对多关系使同一联系人可拥有任意多条手机、邮箱、微信、QQ、微博和地址，而不是把号码限制为单一字段。`favorite` 建索引支撑收藏筛选。

## 3. 核心功能实现

### 收藏联系人

列表项和详情均提供星标按钮。点击后调用 `PATCH /api/contacts/{id}/favorite`，数据库更新与界面状态保持同步。“仅看收藏”过滤器与关键词搜索可组合使用。

### 多种联系方式

编辑器支持动态添加/删除联系方式行，每行包含类型、值与可选标签。保存时在事务中更新联系人主体并重建其联系方式，避免部分写入；空行被忽略。V1.1 前端会在编辑时回填原标签并随每条联系方式提交，避免重新保存时丢失。旧数据库若缺少 `label` 列，启动时补列并以空字符串作为默认值。

### Excel 导出

表头固定为：姓名、收藏、手机、电话、邮箱、微信、QQ、微博、地址、其他联系方式、备注。每个联系人占一行；同类型多个值使用中文分号 `；` 分隔。冻结表头、开启筛选、调整列宽并设置表头样式，导出文件可直接用 Excel/WPS 打开。

V1.1 在存在非空标签时增加“联系方式标签”工作表；主表列结构不变。标签表通过主表行号、类型、同类型序号和原值关联，导入时校验对应关系。没有标签表的 V1.0 工作簿仍照常导入。

### Excel 导入

仅接受 `.xlsx`，限制文件为 5 MiB。校验表头后逐行解析，姓名必填；收藏支持“是/否、1/0、true/false”等常见值。默认遇到同名联系人跳过，避免意外覆盖；结果返回新增数、跳过数及逐行错误。所有有效行在一个事务中写入，任何行错误则整批不导入，以保证可预期性。

## 4. 接口摘要

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/contacts` | 列表、关键词搜索、收藏筛选 |
| POST | `/api/contacts` | 新建联系人 |
| GET | `/api/contacts/{id}` | 联系人详情 |
| PUT | `/api/contacts/{id}` | 更新联系人及全部联系方式 |
| DELETE | `/api/contacts/{id}` | 删除联系人 |
| PATCH | `/api/contacts/{id}/favorite` | 设置/切换收藏 |
| GET | `/api/contacts/export` | 导出 Excel |
| GET | `/api/contacts/template` | 下载导入模板 |
| POST | `/api/contacts/import` | 导入 Excel |

## 5. 异常与数据安全

- 所有 SQL 使用参数化查询；数据库外键开启。
- 请求体、姓名长度、联系方式数量、值长度均校验。
- Excel 不信任文件扩展名之外的任何内容，仅解析工作簿值，不执行宏。
- 删除操作需要界面二次确认。
- 本地数据库不提交 Git；演示数据均为虚构。

## 6. 可复现性与部署

依赖固定在 `requirements.txt`；启动时自动建表。提供示例数据脚本、导入模板、自动化测试及 Dockerfile。公网部署属于可选加分项，实际提交必须填写可公开访问的 URL，`localhost` 不算云部署。
