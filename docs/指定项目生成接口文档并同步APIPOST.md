# 指定项目生成接口文档并同步 APIPOST

适用于项目仓库和 `document` 发布仓库位于任意磁盘、任意目录的情况。

## 一次性准备

1. 安装 Git 和 Python 3；PowerShell 中执行 `git --version`、`py -3 --version` 均应能显示版本号。
2. 从 GitHub 拉取 `document` 仓库到任意本机位置：

   ```powershell
   git clone https://github.com/nagizzz/document.git
   ```

3. 拉取或已有需要维护的项目仓库。项目仓库与 `document` 仓库可以位于不同盘符、不同父目录。
4. 首次发布前确认自己具有 `document` 仓库的 GitHub 推送权限，并完成 GitHub 登录或令牌认证。

## 可直接复制的需求说明

### 已有项目：新增或修改一个接口

> 请按照项目中的《项目文档生成规范》，为 A 接口生成或更新前端 OpenAPI 文档；完成后同步到 `document` 仓库并推送 GitHub，使 APIPOST 自动同步最新接口文档。

将 “A 接口” 替换为实际接口路径、方法和需求；同时提供项目仓库目录，便于定位正确项目。

### 新项目：初始化统一规范

> 请为新项目初始化项目资料库，并完全按 `stone365_user_api` 的《项目文档生成规范》执行。前端接口文档按“一个 HTTP 方法 + 一条接口路径一个 OpenAPI JSON 文件”生成，目录镜像实际控制器目录；源文件使用 `{{项目仓库名}}` 占位符。接口文档、开发记录、项目分析和接入说明均放入 `项目资料库` 的对应目录。完成后按 `document` 仓库操作手册聚合、推送 GitHub，并配置 APIPOST 使用 Raw 聚合地址同步。

其中 `{{项目仓库名}}` 必须替换为实际仓库目录名，例如仓库名为 `demo_api` 时使用 `{{demo_api}}`。

## 1. 指定项目并生成源接口文档

以实际项目仓库目录替换下文的 `<项目仓库目录>`；不要复制示例路径本身。

1. 修改接口代码后，先查看项目根目录的 `项目文档生成规范.md`。
2. 在 `<项目仓库目录>/项目资料库/前端接口文档/` 下维护接口文档：
   - 一个 `HTTP 方法 + 接口路径` 对应一个 `.openapi.json` 文件；
   - 目录镜像实际控制器相对目录；
   - 文件名使用接口路径段以 `-` 连接；POST 不加方法后缀，其他方法追加 `-get`、`-put` 等；
   - `x-controller` 写真实控制器路径，`tags` 写控制器相对目录；
   - 源文件使用 `servers.url={{项目仓库名}}` 与 `{{项目仓库名}}/接口路径`；
   - 在具体接口的 paths 下直接展开请求体与 200 成功响应的字段、说明和示例，避免只写深层 `$ref`、`oneOf`、`allOf`，否则 APIPOST 可能显示空参数。
3. 接入、第三方或流程说明 Markdown 放在 `项目资料库/接入说明/`，不要放在 `前端接口文档/`。
4. 校验新增 JSON。例如：

   ```powershell
   py -3 -c "import json, pathlib; json.load(open(pathlib.Path(r'<接口文件完整路径>'), encoding='utf-8')); print('JSON OK')"
   ```

5. 如项目仓库需要留存本次文档修改，按该项目正常流程单独提交和推送。下面的发布脚本不会提交项目仓库，只会提交 `document` 仓库的聚合文件。

## 2. 发布指定项目的聚合文档

1. 在 `document` 仓库根目录打开 PowerShell。
2. 执行下面命令，并把引号中的内容替换为**目标项目仓库的完整目录**：

   ```powershell
   .\tools\Sync-OpenApiDocs.cmd "<项目仓库目录>"
   ```

   例如项目仓库位于 `E:\Work\backend\stone365_user_api`，则命令为：

   ```powershell
   .\tools\Sync-OpenApiDocs.cmd "E:\Work\backend\stone365_user_api"
   ```

3. 脚本会读取该项目的 `项目资料库/前端接口文档/**/*.openapi.json`，生成 `document/openapi/<项目仓库名>.openapi.json`，然后自动提交并推送到 GitHub。
4. 指定单个项目时，脚本只更新这个项目的聚合文件，不会删除其他项目已发布的聚合文档。
5. 如终端提示需要登录 GitHub，完成登录后重新执行命令。看到推送成功且窗口提示完成即可关闭。

> 若要一次发布多个项目，可把参数改为这些项目共同的上级目录；不传参数则沿用维护者本机配置的默认源目录。

## 3. 在 APIPOST 设置云端同步

首次设置某个项目时，在 APIPOST 中新建或编辑“同步任务”：

1. 数据源名称填写项目仓库名，例如 `stone365_user_api`。
2. 数据源格式选择 `OpenAPI`。
3. 数据源 URL 填写 GitHub Raw 聚合地址：

   ```text
   https://raw.githubusercontent.com/nagizzz/document/main/openapi/<项目仓库名>.openapi.json
   ```

   例如：

   ```text
   https://raw.githubusercontent.com/nagizzz/document/main/openapi/stone365_user_api.openapi.json
   ```

4. 选择手动触发或合适的定时频率，保存后点击“立即导入”验证。
5. 不要把项目内的源文件直接作为 APIPOST 云端同步 URL。源文件包含 `{{项目仓库名}}` 占位符，APIPOST 云端校验可能提示“云端参数错误”；GitHub 聚合副本已自动转换为标准 `/接口路径`。

## 4. 配置域名与对外分享

1. 在 APIPOST 的目标环境创建服务，服务名填写项目仓库名。
2. 前置 URL 填写实际完整域名，例如 `https://api.example.com`，并保存为**云端值**。
3. 对外分享文档时，在分享设置的“开发环境”中选择这个已配置服务的环境。
4. 若共享页只显示“默认环境”或没有域名，检查：服务是否保存为云端值，以及分享时是否已选择对应开发环境。

## 日常更新顺序

```text
修改接口代码
    ↓
更新项目内单接口 OpenAPI JSON 与必要说明
    ↓
提交项目仓库（如项目要求）
    ↓
在 document 仓库执行 Sync-OpenApiDocs.cmd "目标项目目录"
    ↓
脚本推送 GitHub 聚合 JSON
    ↓
APIPOST 按同步频率更新，或手动“立即导入”
```

## 常见问题

| 问题 | 处理方式 |
| --- | --- |
| `py` 或 `python` 找不到 | 安装 Python 3，并重新打开 PowerShell。 |
| GitHub 推送失败 | 确认已登录 GitHub、拥有 `document` 仓库写入权限，以及网络/代理可访问 GitHub 443。 |
| APIPOST 提示“云端参数错误” | 确认填写的是 GitHub Raw 聚合地址，而非项目内含 `{{...}}` 的源文件。 |
| APIPOST 参数区域为空 | 回到源 OpenAPI 文件，把请求体与 200 成功响应的主要字段直接展开在 paths 下，减少深层引用和 `oneOf`/`allOf`。 |
| 共享文档没有域名 | 在 APIPOST 服务中填写前置 URL 为云端值，并在分享设置中选择该环境。 |

## 安全要求

`document` 是公开仓库。不要在字段说明、示例、扩展字段或响应样例中写入密码、Token、内部 IP、真实手机号、身份证号或其他敏感数据。
