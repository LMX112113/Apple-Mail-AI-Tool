#!/bin/bash
# Apple Mail AI 增强工具 - 安装脚本

set -e

echo "=========================================="
echo "    Apple Mail AI 增强工具 - 安装程序"
echo "=========================================="
echo ""

HOME_DIR="$HOME"
INSTALL_DIR="$HOME_DIR/.claude/scripts/ai-mail"
PLIST_NAME="com.user.ai-mail"
PLIST_DST="$HOME_DIR/Library/LaunchAgents/$PLIST_NAME.plist"
SCRIPT_PATH="$INSTALL_DIR/ai_mail.py"

# 获取脚本所在目录（支持从安装包运行）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/8] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "  ❌ 未找到 python3，请先安装 Python 3"
    exit 1
fi
PYTHON_PATH="$(which python3)"
echo "  ✓ Python: $PYTHON_PATH ($(python3 --version))"

echo "[2/8] 安装依赖..."
$PYTHON_PATH -m pip install --user --break-system-packages --quiet rumps anthropic 2>/dev/null || $PYTHON_PATH -m pip install --user --quiet rumps anthropic 2>/dev/null || pip3 install --quiet rumps anthropic
echo "  ✓ rumps + anthropic 已安装"

echo "[3/8] 创建安装目录..."
mkdir -p "$INSTALL_DIR"

echo "[4/8] 停止旧服务..."
launchctl unload "$PLIST_DST" 2>/dev/null || true
# 杀掉旧的菜单栏进程
pkill -f "ai_mail.py" 2>/dev/null || true
sleep 1

echo "[5/8] 复制文件..."
cp "$SCRIPT_DIR/ai_mail.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/mail_reader.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/ai_engine.py" "$INSTALL_DIR/"
# 只在 config.json 不存在时复制（不覆盖用户已有配置）
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    cp "$SCRIPT_DIR/config.json" "$INSTALL_DIR/"
fi
chmod +x "$INSTALL_DIR/ai_mail.py"
echo "  ✓ 文件已安装到: $INSTALL_DIR"

echo "[6/8] 配置开机自启..."
cat > "$PLIST_DST" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$SCRIPT_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/launchd.err</string>
</dict>
</plist>
PLIST_EOF

launchctl load "$PLIST_DST"
echo "  ✓ 开机自启已配置"

echo "[7/8] 启动菜单栏应用..."
# 等待一下让 LaunchAgent 启动
sleep 2

# 如果 LaunchAgent 没有自动启动，手动启动
if ! pgrep -f "ai_mail.py" > /dev/null 2>&1; then
    nohup $PYTHON_PATH "$SCRIPT_PATH" > /dev/null 2>&1 &
    sleep 1
fi

if pgrep -f "ai_mail.py" > /dev/null 2>&1; then
    echo "  ✓ 菜单栏应用已启动"
else
    echo "  ⚠️ 启动失败，请手动运行: $PYTHON_PATH $SCRIPT_PATH"
fi

echo "[8/8] 创建桌面快捷方式..."
cat > /tmp/ai_mail_launcher.applescript << 'APPLESCRIPT_EOF'
set scriptPath to "SCRIPT_PATH_PLACEHOLDER"
set pythonPath to "PYTHON_PATH_PLACEHOLDER"

set runningCount to do shell script "pgrep -f 'ai_mail.py' | wc -l"
if runningCount as integer > 0 then
    display notification "AI Mail 已在运行中" with title "📬 无需重复启动"
    return
end if

tell application "System Events"
    if not (exists file scriptPath) then
        display dialog "AI Mail 未安装，请先运行 install.sh" buttons {"确定"} default button 1 with icon stop
        return
    end if
end tell

try
    do shell script pythonPath & " " & quoted form of scriptPath & " &"
    display notification "AI Mail 已启动" with title "✅ 启动成功"
on error errMsg
    display dialog "启动失败：" & return & errMsg buttons {"确定"} default button 1 with icon stop
end try
APPLESCRIPT_EOF

sed "s|SCRIPT_PATH_PLACEHOLDER|$SCRIPT_PATH|g; s|PYTHON_PATH_PLACEHOLDER|$PYTHON_PATH|g" /tmp/ai_mail_launcher.applescript > /tmp/ai_mail_launcher_final.applescript
osacompile -o "$HOME_DIR/Desktop/AI邮件助手.app" /tmp/ai_mail_launcher_final.applescript 2>/dev/null
rm -f /tmp/ai_mail_launcher.applescript /tmp/ai_mail_launcher_final.applescript

if [ -d "$HOME_DIR/Desktop/AI邮件助手.app" ]; then
    echo "  ✓ 桌面快捷方式已创建: ~/Desktop/AI邮件助手.app"
else
    echo "  ⚠️ 桌面快捷方式创建失败"
fi

echo ""
echo "=========================================="
echo "    ✅ 安装完成！"
echo "=========================================="
echo ""
echo "功能说明："
echo "  📬 菜单栏图标显示未读邮件数"
echo "  📬 最新摘要 - 查看上次总结结果"
echo "  🔄 立即总结 - 立即总结未读邮件并推送通知"
echo "  ✏️ AI 写邮件 - AI 帮你撰写邮件"
echo "  ↩️ AI 回复 - 对选中邮件 AI 生成回复"
echo "  ✅ 一键全部已读 - 标记所有邮件已读"
echo "  📅 添加到日历/提醒 - 选中邮件添加到日历或提醒事项"
echo "  ⚙️ 打开配置 - 编辑 config.json"
echo ""
echo "配置文件: $INSTALL_DIR/config.json"
echo "管理命令："
echo "  停止: launchctl unload ~/Library/LaunchAgents/$PLIST_NAME.plist"
echo "  启动: launchctl load ~/Library/LaunchAgents/$PLIST_NAME.plist"
echo "  卸载: bash uninstall.sh"
echo ""
echo "💡 提示：请确保已设置环境变量 ANTHROPIC_API_KEY 或在配置文件中填写 api_key"
echo ""
