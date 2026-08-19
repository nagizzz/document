# 接口文档发布仓库

此仓库只保存可公开共享的 OpenAPI 文档，不保存后端源代码、账号、密钥或真实用户数据。

## 文档地址

APIPOST 请使用下列 Raw URL 作为“实时同步数据源”：

- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/project_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/stone365_user_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/stone365_member_web.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/cbmnet_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/ccement_enterprise_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/ccement_user_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/ccement_user_behavior_api.openapi.json`
- `https://raw.githubusercontent.com/nagizzz/document/main/openapi/ads_api.openapi.json`

每个文件由 `tools/build_openapi.py` 从指定项目目录（或其上级仓库目录）下各仓库的 `项目资料库\前端接口文档\*.openapi.json` 自动聚合生成，文件名按项目仓库名称命名。源仓库中每个接口各占一个文件；发布副本会将同一控制器的接口保留为相同 OpenAPI 标签，APIPOST 导入后会按标签显示为控制器目录。发布副本会将 paths 中的 `{{环境变量}}/path` 转换为标准 OpenAPI `/path`，并移除 `servers` 中的 APIPOST 占位符，以便云端同步校验。

导入后，在 APIPOST 的目标环境中创建一个以仓库名命名的服务（例如 `stone365_user_api`），前置 URL 填写完整域名（例如 `https://www.user.com`）。对外共享时，在共享设置的“开发环境”中勾选该环境；服务地址和域名变量必须保存为云端值，不能只保存为本地值。共享页显示“默认环境”且没有域名时，通常是未选择该开发环境或默认环境没有配置服务。

## 更新和发布

在 Windows 上可双击 `tools\Sync-OpenApiDocs.cmd`；若项目仓库不在默认目录，推荐在 `document` 仓库根目录打开 PowerShell 并运行：

```powershell
.\tools\Sync-OpenApiDocs.cmd "C:\你的目录\目标项目仓库"
```

参数可以是单个项目仓库，也可以是包含多个项目仓库的上级目录。指定单个项目时，脚本只更新该项目的聚合文件，并保留其他项目已经发布的聚合文件。脚本会重新生成文档、提交变更并推送到 GitHub；首次推送时 Git 可能要求完成 GitHub 登录或令牌认证。

## 安全要求

- 此仓库是公开仓库，任何人均可读取其中内容。
- 不要在 OpenAPI 示例、描述或扩展字段中放入密码、Token、内部 IP、手机号、身份证号或真实业务敏感数据。
- 有破坏性接口变更时，请同步更新变更说明并通知对接人。
