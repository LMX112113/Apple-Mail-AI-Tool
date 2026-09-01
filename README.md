# Apple Mail AI 增强工具

macOS Apple Mail AI 增强工具，菜单栏常驻，支持 AI 总结邮件、写邮件、自动删除、一键已读等功能。

## ✨ 核心功能

### 📬 邮件总结
- **定时自动总结**：每 4 小时自动总结未读邮件，macOS 通知中心推送
- **手动立即总结**：随时触发 AI 总结，生成 HTML 桌面窗口显示
- **多文件夹支持**：可同时扫描 INBOX 和自定义文件夹（如"刘俊峰、一级总"）
- **按发件人分组**：总结按发件人分组，清晰明了

### ✏️ AI 邮件操作
- **AI 写邮件**：输入主题和要点，AI 自动生成邮件（固定签名"李明星"）
- **AI 回复**：对选中邮件 AI 生成专业回复
- **确认机制**：生成后弹窗预览，确认后才创建草稿

### 🗑️ 邮件清理
- **自动删除规则**：定时自动删除指定发件人的邮件（如 gfplansrv@yonyou.com）
- **手动清理按钮**：一键清理匹配的邮件，删除前显示数量并确认
- **支持已读邮件**：删除功能扫描所有邮件（包括已读和未读）

### 🔧 智能过滤
- **仅统计规则**：某些邮件只统计数量，不总结内容（适合通知类、工单类）
- **排除规则**：完全忽略某些邮件（如营销邮件、系统通知）
- **包含规则**：默认总结所有其他邮件

### 📅 其他功能
- **一键全部已读**：批量标记收件箱所有邮件为已读
- **添加到日历/提醒**：选中邮件，AI 提取信息后添加到日历或提醒事项
- **桌面窗口显示**：总结内容以 HTML 形式在浏览器中展示
- **后台执行**：所有 AI 操作在后台线程执行，不卡菜单

## 📦 安装前准备

1. **Python 3**（macOS 自带或从 python.org 安装）
2. **pip 包**：
   ```bash
   pip3 install rumps anthropic
   ```
3. **API Key**：二选一
   - 设置环境变量：`export ANTHROPIC_API_KEY=sk-ant-xxx`
   - 或安装后编辑配置文件（见下方）

## 🚀 安装

```bash
# 解压安装包
unzip ~/Downloads/Apple-Mail-AI-工具.zip
cd Apple-Mail-AI-工具

# 运行安装脚本
chmod +x install.sh
./install.sh
```

安装后菜单栏会出现 📬 图标，显示未读邮件数量。

## ⚙️ 配置

安装后编辑 `~/.claude/scripts/ai-mail/config.json`：

### API 配置
```json
{
  "api": {
    "api_key": "sk-ant-xxx",
    "model": "qwen3.7-plus",
    "max_tokens": 2000,
    "base_url": "https://XXXX"
  }
}
```

### 邮件扫描配置
```json
{
  "mail": {
    "max_emails_per_summary": 20,
    "folders": ["INBOX", "YYYYY"]
  }
}
```
- `max_emails_per_summary`：每次最多扫描多少封邮件
- `folders`：扫描的邮箱文件夹列表

### 过滤规则配置

#### 自动删除规则
```json
{
  "auto_delete_rules": [
    {
      "field": "sender",
      "contains": "XXX@YYYY.com"
    }
  ]
}
```
匹配的邮件会被自动删除（定时任务 + 手动按钮）

#### 仅统计规则
```json
{
  "count_only_rules": [
    {
      "field": "sender",
      "contains": "XXX@YYYY.com|XXX@YYYY.com"
    }
  ]
}
```
匹配的邮件只显示发件人和数量，不总结内容

#### 排除规则
```json
{
  "exclude_rules": [
    {
      "field": "sender",
      "contains": "noreply|no-reply|mailer-daemon|postmaster"
    },
    {
      "field": "subject",
      "contains": "退订|unsubscribe|促销|广告"
    }
  ]
}
```
匹配的邮件完全忽略，不统计也不总结

#### 包含规则
```json
{
  "include_rules": [
    {
      "field": "sender",
      "contains": ".*"
    }
  ]
}
```
默认包含所有其他邮件进行总结

### 定时任务配置
```json
{
  "schedule": {
    "interval_hours": 4,
    "daily_time": "09:00"
  }
}
```
- `interval_hours`：自动总结间隔（小时），0 表示不自动总结
- `daily_time`：每天定时总结时间

## 📖 使用说明

### 菜单栏操作

点击菜单栏 📬 图标，下拉菜单包含：

1. **📋 查看总结（桌面窗口）**：在浏览器中打开 HTML 总结
2. **📬 最新摘要（弹窗）**：弹窗显示上次总结内容
3. **🔄 立即总结**：手动触发 AI 总结（后台执行）
4. **🗑️ 清理指定邮件**：手动删除配置的自动删除规则匹配的邮件
5. **✏️ AI 写邮件**：输入要点，AI 生成邮件草稿
6. **↩️ AI 回复选中邮件**：对 Mail 中选中的邮件生成回复
7. **✅ 一键全部已读**：标记所有邮件为已读
8. **📅 添加到日历/提醒**：将选中邮件添加到日历或提醒事项
9. **⚙️ 打开配置**：打开配置文件
10. **🚪 退出**：退出应用



## 🗑️ 卸载

```bash
cd ~/apple-mail-ai-tool  # 或安装包目录
chmod +x uninstall.sh
./uninstall.sh
```

卸载会删除：
- 程序文件（~/.claude/scripts/ai-mail/）
- LaunchAgent（开机自启）
- 桌面快捷方式

## 🔒 安全说明

- API Key 存储在配置文件中，建议设置文件权限：`chmod 600 ~/.claude/scripts/ai-mail/config.json`
- 安装包中不包含 API Key，需用户自行配置
- 所有 AI 操作在本地执行，不上传邮件内容到第三方

## 🛠️ 技术架构

- **Python 3.8+**：主程序语言
- **rumps**：macOS 菜单栏应用框架
- **Anthropic SDK**：调用 Claude API
- **AppleScript**：通过 osascript 操作 Mail.app、Calendar.app、Reminders.app
- **LaunchAgent**：macOS 服务管理，实现开机自启
- **fcntl 锁文件**：防止重复启动

## 📋 系统要求

- macOS 10.15+
- Python 3.8+
- Apple Mail 已配置邮箱账户
- 网络连接（用于 AI API 调用）

## 🐛 常见问题

**Q: 菜单栏没显示图标？**
A: 检查是否已运行：`ps aux | grep ai_mail.py`，或使用命令启动：
```bash
cd ~/.claude/scripts/ai-mail
python3 ai_mail.py
```

**Q: 总结很慢或卡住？**
A: AI 调用需要 30-60 秒，已在后台执行，不会卡菜单。如仍卡住，检查网络连接和 API Key。

**Q: 某些邮件没被总结？**
A: 检查 config.json 的过滤规则，确认邮件不在 exclude_rules 中。

**Q: 如何修改扫描的文件夹？**
A: 编辑 config.json 的 `mail.folders` 数组，添加文件夹名称。

## 📄 许可证

MIT License

## 🤝 反馈

如有问题或建议，请联系开发者。
