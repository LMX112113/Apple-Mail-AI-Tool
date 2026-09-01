#!/bin/bash
# Apple Mail AI 增强工具 - 卸载脚本

echo "=========================================="
echo "    Apple Mail AI 增强工具 - 卸载程序"
echo "=========================================="
echo ""

HOME_DIR="$HOME"
INSTALL_DIR="$HOME_DIR/.claude/scripts/ai-mail"
PLIST_NAME="com.user.ai-mail"
PLIST_DST="$HOME_DIR/Library/LaunchAgents/$PLIST_NAME.plist"

echo "[1/4] 停止服务..."
launchctl unload "$PLIST_DST" 2>/dev/null || true
pkill -f "ai_mail.py" 2>/dev/null || true
sleep 1
echo "  ✓ 服务已停止"

echo "[2/4] 删除 LaunchAgent..."
rm -f "$PLIST_DST"
echo "  ✓ LaunchAgent 已删除"

echo "[3/4] 删除安装文件..."
rm -rf "$INSTALL_DIR"
echo "  ✓ 安装目录已删除"

echo "[4/4] 清理完成"
echo ""
echo "=========================================="
echo "    ✅ 卸载完成！"
echo "=========================================="
echo ""
echo "提示：Python 依赖包 (rumps, anthropic) 未自动卸载"
echo "如需卸载：pip3 uninstall rumps anthropic"
echo ""
