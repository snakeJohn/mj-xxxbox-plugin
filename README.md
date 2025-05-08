# MidJourney 微信插件

本插件可以在微信中使用 MidJourney AI 绘图功能。

## 功能特点

- 支持 MidJourney 的主要功能：绘图、放大、变换、垫图、混图、识图等
- 支持用户权限管理：管理员用户、白名单/黑名单用户和群组
- 支持每日使用次数限制
- 简单易用的命令系统

## 安装方法

1. 确保已安装 Python 3.7+ 和相关依赖
2. 将本插件文件夹放入项目的 `plugins` 目录下
3. 修改 `config.toml` 文件配置 MidJourney API 参数

## 配置说明

编辑 `config.toml` 文件：

```toml
# MidJourney API 配置
mj_url = "https://your-midjourney-api.com"  # MidJourney API 地址
mj_api_secret = "your-api-secret"  # API密钥
mj_tip = true  # 是否显示提示
mj_admin_password = "admin-password"  # 管理员密码
discordapp_proxy = "https://your-discord-proxy.com"  # Discord代理服务器（可选）

# 使用限制
daily_limit = 3  # 每日使用次数限制

# 命令前缀配置（可自定义）
imagine_prefix = ["/i", "/mj"]  # 绘图命令
# ...其他命令配置...
```

## 使用方法

### 基本命令

- `/i [提示词]` 或 `/mj [提示词]`：生成图片
- `/f [任务ID]`：查询任务状态
- `/u [任务ID] [U1-U4/V1-V4]`：放大或变换图片
- `/p [提示词]`：进入垫图模式，然后发送图片
- `/b`：进入混图模式，发送多张图片后使用 `/e` 结束
- `/d`：进入识图模式，然后发送一张图片
- `/q`：查询当前任务队列
- `/r [任务ID]`：重新生成图片

### 管理命令

管理员可使用以下命令：

- `/mj password [管理密码]`：验证管理员身份
- `/mj addadmin @用户`：添加管理员
- `/mj addgroup`：添加当前群到白名单
- `/mj adduser @用户`：添加用户到白名单
- `/mj blackgroup`：将当前群加入黑名单
- `/mj blackuser @用户`：将用户加入黑名单

## 注意事项

1. 需要有效的 MidJourney API 才能使用
2. 请合理设置使用限制，避免 API 使用超额
3. 使用代理服务器可以改善图片加载速度

## 版本历史

- v1.0.0：初始版本

## 许可证

本插件基于 MIT 许可证开源。

## 鸣谢

- 原始项目作者及地址：[Kylsky](https://github.com/Kylsky/mj-dify-on-wechat-plugin)
- 重构者：snakejohn by cursor
