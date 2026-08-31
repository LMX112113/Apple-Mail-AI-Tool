# Apple Mail AI 增强工具

macOS Apple Mail AI 增强工具，菜单栏常驻，支持 AI 总结邮件、写邮件、一键已读等。

## 功能

- 📬 **定时总结**：自动总结未读邮件，macOS 通知中心推送
- 🔄 **立即总结**：手动触发 AI 总结
- ✏️ **AI 写邮件**：输入要点，AI 帮你撰写邮件
- ↩️ **AI 回复**：对选中邮件 AI 生成回复
- ✅ **一键全部已读**：批量标记所有邮件已读
- 📅 **添加到日历/提醒**：选中邮件添加到日历或提醒事项
- 🔧 **过滤规则**：可配置总结/忽略哪些邮件

## 安装前准备

1. **Python 3**（macOS 自带或从 python.org 安装）
2. **pip 包**：`pip3 install rumps anthropic`
3. **API Key**：设置环境变量 `export ANTHROPIC_API_KEY=sk-ant-xxx`
   或在安装后编辑 `~/.claude/scripts/ai-mail/config.json` 中的 `api_key`

## 安装

```bash
# 进入安装包目录
cd Apple-Mail-AI-工具

# 运行安装脚本
chmod +x install.sh
./install.sh
```

安装后菜单栏会出现 📬 图标。

## 配置

安装后编辑 `~/.claude/scripts/ai-mail/config.json`：

```json
{
  "api": {
    "api_key": "sk-ant-xxx",
    "model": "claude-sonnet-4-20250514"
  },
  "filter": {
    "exclude_rules": [
      {"field": "sender", "contains": "noreply|no-reply", "action": "skip"}
    ],
    "include_rules": [
      {"field": "sender", "contains": "@yourcompany.com", "action": "summarize"}
    ],
    "custom_prompt": "重点关注：财务、审批、紧急事项。"
  },
  "schedule": {
    "interval_hours": 4,
    "daily_time": "09:00"
  }
}
```

## 卸载

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## 系统要求

- macOS 10.15+
- Python 3.8+
- Apple Mail 已配置邮箱账户
