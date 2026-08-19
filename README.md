# 接口文档发布仓库

此仓库只保存可公开共享的 OpenAPI 文档，不保存后端源代码、账号、密钥或真实用户数据。

## 文档地址

APIPOST 请使用下列 Raw URL 作为“实时同步数据源”：

- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/project_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/stone365_user_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/stone365_member_web.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/cbmnet_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/ccement_enterprise_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/ccement_user_behavior_api.openapi.json`

每个文件由 `tools/build_openapi.py` 从 `D:\Code Repositories` 下各仓库的 `项目资料库\前端接口文档\*.openapi.json` 自动聚合生成，文件名按项目仓库名称命名。源仓库中每个接口各占一个文件；发布副本会将同一控制器的接口保留为相同 OpenAPI 标签，APIPOST 导入后会按标签显示为控制器目录。发布副本会保留以仓库名命名的 `servers` 域名占位符（例如 `{{stone365_user_api}}`），同时将 paths 中的 `{{环境变量}}/path` 转换为标准 OpenAPI `/path`，以便云端同步校验。

## 更新和发布

在 Windows 上双击 `tools\Sync-OpenApiDocs.cmd`。该脚本会重新生成文档、提交变更并推送到 GitHub；首次推送时 Git 可能要求完成 GitHub 登录或令牌认证。

## 安全要求

- 此仓库是公开仓库，任何人均可读取其中内容。
- 不要在 OpenAPI 示例、描述或扩展字段中放入密码、Token、内部 IP、手机号、身份证号或真实业务敏感数据。
- 有破坏性接口变更时，请同步更新变更说明并通知对接人。
