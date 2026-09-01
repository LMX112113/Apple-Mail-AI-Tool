#!/bin/bash
# Apple Mail AI 增强工具 - 打包安装包
# 将安装包打包到 ~/Downloads/ 目录

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_NAME="Apple-Mail-AI-工具"
OUTPUT_DIR="$HOME/Downloads"
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/$PACKAGE_NAME"

echo "=========================================="
echo "    打包 Apple Mail AI 增强工具"
echo "=========================================="
echo ""

# 创建包目录结构
mkdir -p "$PACKAGE_DIR"

echo "[1/3] 复制文件..."
cp "$SCRIPT_DIR/ai_mail.py" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/mail_reader.py" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/ai_engine.py" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/config.json" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/install.sh" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/uninstall.sh" "$PACKAGE_DIR/"
chmod +x "$PACKAGE_DIR/install.sh"
chmod +x "$PACKAGE_DIR/uninstall.sh"

# 创建 README
cat > "$PACKAGE_DIR/README.md" << 'EOF'
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
EOF

echo "[2/3] 创建压缩包..."
cd "$TEMP_DIR"
zip -r "$OUTPUT_DIR/${PACKAGE_NAME}.zip" "$PACKAGE_NAME" > /dev/null

# 清理临时目录
rm -rf "$TEMP_DIR"

echo "[3/3] 完成"
echo ""
echo "=========================================="
echo "    ✅ 打包完成！"
echo "=========================================="
echo ""
echo "安装包位置: $OUTPUT_DIR/${PACKAGE_NAME}.zip"
echo ""
echo "安装步骤："
echo "  1. 解压 zip 文件"
echo "  2. 打开终端，cd 到解压后的目录"
echo "  3. 运行: ./install.sh"
echo ""
echo "📦 包大小: $(du -sh "$OUTPUT_DIR/${PACKAGE_NAME}.zip" | cut -f1)"
echo ""
