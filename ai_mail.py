#!/usr/bin/env python3
"""Apple Mail AI 增强工具 - 主程序（菜单栏应用）"""

import os
import sys
import json
import subprocess
import threading
import time
import fcntl

# 确保能找到同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 锁文件防止重复启动
LOCK_FILE = os.path.expanduser("~/.claude/scripts/ai-mail/.lock")

def acquire_lock():
    """获取锁文件，防止重复启动"""
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError):
        return None

def release_lock(lock_fd):
    """释放锁"""
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            os.remove(LOCK_FILE)
        except:
            pass

import rumps
import mail_reader
import ai_engine


# 桌面悬浮窗口（用 HTML 显示邮件总结）
class SummaryWindow:
    """用 HTML 文件显示邮件总结，用浏览器打开"""

    def __init__(self):
        self.html_path = os.path.expanduser("~/.claude/scripts/ai-mail/summary.html")

    def show(self, content):
        """显示总结窗口"""
        try:
            # 转义 HTML 特殊字符
            content_escaped = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>📬 邮件总结</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .content {{
            line-height: 1.8;
            color: #333;
            white-space: pre-wrap;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.9em;
            margin-top: 20px;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📬 邮件总结</h1>
        <div class="content">{content_escaped}</div>
        <div class="timestamp">生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>
</body>
</html>"""

            with open(self.html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # 用默认浏览器打开
            subprocess.run(['open', self.html_path])

        except Exception as e:
            print(f"创建 HTML 失败: {e}")
            # 回退到弹窗
            rumps.alert(title="邮件总结", message=content[:1000])

    def hide(self):
        """隐藏窗口（HTML 方式无需实现）"""
        pass


summary_window = SummaryWindow()


class AIMailApp(rumps.App):
    """Apple Mail AI 菜单栏应用"""

    def __init__(self):
        super().__init__(
            name="AI Mail",
            title="📬",  # 菜单栏图标
            quit_button=None
        )
        self.summary_text = ""
        self.last_summary_time = ""
        self._running_tasks = set()  # 防重复执行
        self._update_unread_count()

        # 构建菜单
        self._build_menu()

        # 启动定时调度
        self._start_scheduler()

    def _try_start_task(self, task_name):
        """尝试启动任务，返回 True 表示可以执行，False 表示已在运行"""
        if task_name in self._running_tasks:
            subprocess.run([
                'osascript', '-e',
                f'display notification "请稍等，上一个操作还在执行中" with title "AI Mail"'
            ])
            return False
        self._running_tasks.add(task_name)
        return True

    def _finish_task(self, task_name):
        """标记任务完成"""
        self._running_tasks.discard(task_name)

    def _build_menu(self):
        """构建菜单栏下拉菜单"""
        self.menu = [
            rumps.MenuItem("📋 查看总结（桌面窗口）", callback=self._show_summary_window),
            rumps.MenuItem("📬 最新摘要（通知）", callback=self._show_summary),
            rumps.MenuItem("🔄 立即总结", callback=self._do_summarize),
            None,  # 分割线
            rumps.MenuItem("🗑️ 清理指定邮件", callback=self._manual_delete),
            None,
            rumps.MenuItem("✏️ AI 写邮件", callback=self._compose_email),
            rumps.MenuItem("↩️ AI 回复选中邮件", callback=self._reply_email),
            None,
            rumps.MenuItem("✅ 一键全部已读", callback=self._mark_all_read),
            rumps.MenuItem("📅 添加到日历/提醒", callback=self._add_to_calendar),
            None,
            rumps.MenuItem("⚙️ 打开配置", callback=self._open_config),
            rumps.MenuItem("🚪 退出", callback=self._quit_app),
        ]

    def _update_unread_count(self):
        """更新未读邮件计数"""
        try:
            count = mail_reader.get_unread_count()
            self.title = f"📬{count}" if count > 0 else "📬"
        except Exception:
            self.title = "📬"

    def _get_schedule_config(self):
        """读取定时调度配置"""
        config_path = os.path.expanduser("~/.claude/scripts/ai-mail/config.json")
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("schedule", {})
        except Exception:
            return {}

    def _get_schedule_times(self):
        """根据 start_time / end_time / interval_hours 计算今天所有提醒时间点

        返回 list of (hour, minute)
        """
        schedule = self._get_schedule_config()
        interval = schedule.get("interval_hours", 3)
        start_str = schedule.get("start_time", "09:00")
        end_str = schedule.get("end_time", "19:00")

        # 兼容旧配置：没有 start_time 时用 daily_time
        if not start_str:
            start_str = schedule.get("daily_time", "09:00")

        try:
            sh, sm = [int(x) for x in start_str.split(":")]
            eh, em = [int(x) for x in end_str.split(":")]
        except Exception:
            sh, sm, eh, em = 9, 0, 19, 0

        if interval <= 0:
            return []

        times = []
        cur = sh * 60 + sm
        end = eh * 60 + em
        while cur <= end:
            times.append((cur // 60, cur % 60))
            cur += interval * 60
        return times

    def _get_auto_show_times(self):
        """获取需要自动打开窗口的时间点列表

        返回 list of "HH:MM" 字符串
        """
        schedule = self._get_schedule_config()
        auto_show = schedule.get("auto_show_times", [])
        if isinstance(auto_show, str):
            auto_show = [auto_show]
        return auto_show

    def _start_scheduler(self):
        """启动定时任务"""
        def scheduler_loop():
            last_run_key = ""  # "YYYY-MM-DD-HH" 防止同一小时重复跑

            while True:
                try:
                    now = time.localtime()
                    now_h, now_m = now.tm_hour, now.tm_min
                    today_key_prefix = time.strftime("%Y-%m-%d")

                    # 计算今天的提醒时间点
                    schedule_times = self._get_schedule_times()
                    should_run = False
                    trigger_time = None
                    for (h, m) in schedule_times:
                        run_key = f"{today_key_prefix}-{h:02d}"
                        # 在当前时间之前或刚好到点（±2分钟窗口）且未跑过
                        if (h < now_h) or (h == now_h and abs(now_m - m) <= 2):
                            if last_run_key != run_key:
                                should_run = True
                                last_run_key = run_key
                                trigger_time = f"{h:02d}:{m:02d}"
                                break

                    if should_run:
                        # 检查是否需要自动打开窗口
                        auto_show_times = self._get_auto_show_times()
                        auto_show_window = trigger_time in auto_show_times
                        self._run_scheduled_task(auto_show_window=auto_show_window)

                    # 自动删除（每次循环都检查）
                    self._run_auto_delete()

                except Exception as e:
                    print(f"Scheduler error: {e}")

                # 每分钟检查一次
                time.sleep(60)

        t = threading.Thread(target=scheduler_loop, daemon=True)
        t.start()

    def _run_auto_delete(self):
        """执行自动删除规则"""
        try:
            filter_config = ai_engine.get_filter_config()
            auto_delete_rules = filter_config.get("auto_delete_rules", [])
            mail_config = ai_engine.get_mail_config()
            folders = mail_config.get("folders", ["INBOX"])

            total_deleted = 0
            for rule in auto_delete_rules:
                if rule.get("field") == "sender":
                    pattern = rule.get("contains", "")
                    if pattern:
                        deleted = mail_reader.delete_emails_from_sender(pattern, folders)
                        total_deleted += deleted

            if total_deleted > 0:
                rumps.notification("AI Mail", f"🗑️ 已删除 {total_deleted} 封邮件", "自动清理完成")
        except Exception as e:
            print(f"Auto delete error: {e}")

    def _run_scheduled_task(self, auto_show_window=False):
        """执行定时总结任务

        Args:
            auto_show_window: 是否自动打开浏览器窗口显示总结
        """
        try:
            mail_config = ai_engine.get_mail_config()
            max_emails = mail_config.get("max_emails_per_summary", 20)
            folders = mail_config.get("folders", ["INBOX"])

            emails = mail_reader.get_unread_emails(max_emails, folders)
            normal_emails, count_only_emails = ai_engine.filter_emails(emails)

            if normal_emails or count_only_emails:
                summary = ai_engine.summarize_emails(normal_emails, count_only_emails)
                self.summary_text = summary
                self.last_summary_time = time.strftime("%H:%M")

                total_count = len(normal_emails) + len(count_only_emails)
                rumps.notification(
                    title=f"📬 {total_count}封新邮件摘要",
                    subtitle=self.last_summary_time,
                    message=summary[:200] + ("..." if len(summary) > 200 else "")
                )

                # 如果配置了自动打开窗口，则打开浏览器显示总结
                if auto_show_window:
                    summary_window.show(summary)

            self._update_unread_count()
        except Exception as e:
            print(f"Scheduled task error: {e}")

    @rumps.clicked("📬 最新摘要（通知）")
    def _show_summary(self, _):
        """显示上次总结结果（右上角通知）"""
        import os
        with open('/tmp/ai_mail_debug.log', 'a') as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] _show_summary 被调用, summary_text长度: {len(self.summary_text)}\n")

        if self.summary_text:
            # 用 osascript 显示通知（更可靠）
            msg = self.summary_text[:200] + ("..." if len(self.summary_text) > 200 else "")
            msg_escaped = msg.replace('"', '\\"')
            subprocess.run([
                'osascript', '-e',
                f'display notification "{msg_escaped}" with title "📬 最新摘要 ({self.last_summary_time})"'
            ])
            with open('/tmp/ai_mail_debug.log', 'a') as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] osascript 通知已发送\n")
        else:
            subprocess.run([
                'osascript', '-e',
                'display notification "请先点击「立即总结」" with title "AI Mail" subtitle "暂无摘要"'
            ])
            with open('/tmp/ai_mail_debug.log', 'a') as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] 无摘要，osascript 已提示\n")

    @rumps.clicked("📋 查看总结（桌面窗口）")
    def _show_summary_window(self, _):
        """在桌面窗口显示总结"""
        if self.summary_text:
            summary_window.show(self.summary_text)
        else:
            rumps.alert(title="暂无摘要", message="请先点击「立即总结」")

    @rumps.clicked("🔄 立即总结")
    def _do_summarize(self, _):
        """立即执行邮件总结（后台执行）"""
        if not self._try_start_task("summarize"):
            return

        def do_summary():
            try:
                rumps.notification("AI Mail", "🔄 正在总结", "AI 正在分析未读邮件，请稍候...")

                mail_config = ai_engine.get_mail_config()
                max_emails = mail_config.get("max_emails_per_summary", 20)
                folders = mail_config.get("folders", ["INBOX"])

                emails = mail_reader.get_unread_emails(max_emails, folders)
                normal_emails, count_only_emails = ai_engine.filter_emails(emails)

                if not normal_emails and not count_only_emails:
                    rumps.notification("AI Mail", "✅ 完成", "没有需要总结的未读邮件。")
                    self._update_unread_count()
                    return

                summary = ai_engine.summarize_emails(normal_emails, count_only_emails)
                self.summary_text = summary
                self.last_summary_time = time.strftime("%H:%M")

                total_count = len(normal_emails) + len(count_only_emails)
                rumps.notification(
                    title=f"✅ {total_count}封邮件已总结",
                    subtitle=self.last_summary_time,
                    message="正在打开总结窗口..."
                )

                # 自动打开桌面窗口显示总结
                summary_window.show(summary)

                self._update_unread_count()

            except Exception as e:
                rumps.notification("AI Mail", "❌ 错误", str(e))
                self._update_unread_count()
            finally:
                self._finish_task("summarize")

        # 后台线程执行
        threading.Thread(target=do_summary, daemon=True).start()

    @rumps.clicked("🗑️ 清理指定邮件")
    def _manual_delete(self, _):
        """手动清理配置中指定的邮件（后台执行）"""
        if not self._try_start_task("delete"):
            return

        # 写入日志文件
        with open('/tmp/ai_mail_debug.log', 'a') as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] _manual_delete 被调用\n")

        def do_delete():
            try:
                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] do_delete 开始执行\n")

                filter_config = ai_engine.get_filter_config()
                auto_delete_rules = filter_config.get("auto_delete_rules", [])

                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] auto_delete_rules: {auto_delete_rules}\n")

                # 先统计每个规则会删除多少邮件
                mail_config = ai_engine.get_mail_config()
                folders = mail_config.get("folders", ["INBOX"])

                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] folders: {folders}\n")

                delete_info = []
                for rule in auto_delete_rules:
                    if rule.get("field") == "sender":
                        pattern = rule.get("contains", "")
                        if pattern:
                            with open('/tmp/ai_mail_debug.log', 'a') as f:
                                f.write(f"[{time.strftime('%H:%M:%S')}] 检查规则: {pattern}\n")
                            # 扫描所有邮件（包括已读）统计数量
                            count = mail_reader.count_emails_from_sender(pattern, folders)
                            with open('/tmp/ai_mail_debug.log', 'a') as f:
                                f.write(f"[{time.strftime('%H:%M:%S')}] 找到 {count} 封邮件\n")
                            if count > 0:
                                delete_info.append(f"{pattern}: {count}封")

                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] delete_info: {delete_info}\n")

                if not delete_info:
                    with open('/tmp/ai_mail_debug.log', 'a') as f:
                        f.write(f"[{time.strftime('%H:%M:%S')}] 没有匹配的邮件，显示通知\n")
                    rumps.notification("AI Mail", "✅ 无需清理", "没有匹配的邮件")
                    return

                # 显示确认对话框
                info_text = "\n".join(delete_info)
                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] 准备显示确认对话框: {info_text}\n")

                try:
                    result = subprocess.run(
                        ['osascript', '-e', f'display dialog "将删除以下邮件：\n\n{info_text}\n\n确定删除？" with title "确认删除" buttons {{"取消", "确定"}} default button "确定"'],
                        capture_output=True, text=True, timeout=300, check=True
                    )
                    with open('/tmp/ai_mail_debug.log', 'a') as f:
                        f.write(f"[{time.strftime('%H:%M:%S')}] 用户点击确定\n")
                except subprocess.CalledProcessError:
                    # 用户点击了取消
                    with open('/tmp/ai_mail_debug.log', 'a') as f:
                        f.write(f"[{time.strftime('%H:%M:%S')}] 用户取消\n")
                    return

                # 执行删除
                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] 开始执行删除\n")

                rumps.notification("AI Mail", "🔄 删除中", "正在删除邮件...")
                total_deleted = 0
                for rule in auto_delete_rules:
                    if rule.get("field") == "sender":
                        pattern = rule.get("contains", "")
                        if pattern:
                            with open('/tmp/ai_mail_debug.log', 'a') as f:
                                f.write(f"[{time.strftime('%H:%M:%S')}] 调用 delete_emails_from_sender: {pattern}\n")
                            deleted = mail_reader.delete_emails_from_sender(pattern, folders)
                            with open('/tmp/ai_mail_debug.log', 'a') as f:
                                f.write(f"[{time.strftime('%H:%M:%S')}] 删除了 {deleted} 封\n")
                            total_deleted += deleted

                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] 总共删除: {total_deleted}\n")

                rumps.notification("AI Mail", f"🗑️ 已删除 {total_deleted} 封邮件", "清理完成")
                self._update_unread_count()

            except Exception as e:
                with open('/tmp/ai_mail_debug.log', 'a') as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] 异常: {e}\n")
                rumps.notification("AI Mail", "❌ 错误", str(e))
            finally:
                self._finish_task("delete")

        threading.Thread(target=do_delete, daemon=True).start()

    @rumps.clicked("✏️ AI 写邮件")
    def _compose_email(self, _):
        """AI 写邮件（后台执行）"""
        if not self._try_start_task("compose"):
            return

        # 用 macOS 原生对话框获取输入（不阻塞菜单）
        try:
            result = subprocess.run(
                ['osascript', '-e', 'text returned of (display dialog "请输入邮件主题方向和要点：" default answer "" with title "AI 写邮件" buttons {"取消", "生成"} default button "生成")'],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                self._finish_task("compose")
                return  # 用户取消
            response = result.stdout.strip()
            if not response:
                self._finish_task("compose")
                return
        except Exception:
            self._finish_task("compose")
            return

        def do_compose():
            try:
                rumps.notification("AI Mail", "🔄 AI 写邮件中", "正在生成邮件内容，请稍候...")
                subject, body, full_text = ai_engine.compose_email(response, response)
                if not body:
                    body = full_text

                # 用原生对话框确认
                preview = f"主题：{subject}\n\n{body[:300]}..."
                result = subprocess.run(
                    ['osascript', '-e', f'display dialog "{preview}" with title "邮件预览" buttons {{"取消", "创建草稿"}} default button "创建草稿"'],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode != 0:
                    return  # 用户取消

                mail_reader.create_draft(subject=subject, body=body)
                rumps.notification("AI Mail", "✅ 已创建", "草稿已在 Mail 中打开")
            except Exception as e:
                rumps.notification("AI Mail", "❌ 错误", str(e))
            finally:
                self._finish_task("compose")

        threading.Thread(target=do_compose, daemon=True).start()

    @rumps.clicked("↩️ AI 回复选中邮件")
    def _reply_email(self, _):
        """AI 回复选中邮件（后台执行）"""
        if not self._try_start_task("reply"):
            return

        try:
            email = mail_reader.get_selected_email()
            if not email:
                rumps.notification("AI Mail", "提示", "请先在 Mail 中选中一封邮件")
                self._finish_task("reply")
                return
        except Exception as e:
            rumps.notification("AI Mail", "错误", str(e))
            self._finish_task("reply")
            return

        def do_reply():
            try:
                rumps.notification("AI Mail", "🔄 AI 生成回复中", "正在分析邮件内容，请稍候...")
                reply_text = ai_engine.generate_reply(email)

                # 用原生对话框确认
                preview = f"Re: {email.get('subject', '')}\n\n{reply_text[:300]}..."
                result = subprocess.run(
                    ['osascript', '-e', f'display dialog "{preview}" with title "回复预览" buttons {{"取消", "创建回复"}} default button "创建回复"'],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode != 0:
                    return  # 用户取消

                mail_reader.reply_to_email(email, reply_text)
                rumps.notification("AI Mail", "✅ 已创建", "回复草稿已在 Mail 中打开")
            except Exception as e:
                rumps.notification("AI Mail", "❌ 错误", str(e))
            finally:
                self._finish_task("reply")

        threading.Thread(target=do_reply, daemon=True).start()

    @rumps.clicked("✅ 一键全部已读")
    def _mark_all_read(self, _):
        """标记所有邮件已读（后台执行）"""
        if not self._try_start_task("mark_read"):
            return

        try:
            count = mail_reader.get_unread_count()
            if count == 0:
                rumps.notification("AI Mail", "提示", "没有未读邮件")
                self._finish_task("mark_read")
                return

            # 确认对话框（主线程）
            result = subprocess.run(
                ['osascript', '-e', f'display dialog "确定将 {count} 封未读邮件全部标记为已读？" with title "确认" buttons {{"取消", "确定"}} default button "确定"'],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode != 0:
                self._finish_task("mark_read")
                return  # 用户取消

        except Exception as e:
            rumps.notification("AI Mail", "错误", str(e))
            self._finish_task("mark_read")
            return

        def do_mark_read():
            try:
                rumps.notification("AI Mail", "🔄 处理中", "正在标记邮件已读...")
                success = mail_reader.mark_all_read()
                if success:
                    rumps.notification("AI Mail", "✅ 完成", f"已将 {count} 封邮件标记为已读")
                    self._update_unread_count()
                else:
                    rumps.notification("AI Mail", "失败", "操作失败，请检查 Mail 权限")
            except Exception as e:
                rumps.notification("AI Mail", "❌ 错误", str(e))
            finally:
                self._finish_task("mark_read")

        threading.Thread(target=do_mark_read, daemon=True).start()

    @rumps.clicked("📅 添加到日历/提醒")
    def _add_to_calendar(self, _):
        """添加选中邮件到日历/提醒事项（AI 提取在后台执行）"""
        if not self._try_start_task("calendar"):
            return

        try:
            email = mail_reader.get_selected_email()
            if not email:
                rumps.notification("AI Mail", "提示", "请先在 Mail 中选中一封邮件")
                self._finish_task("calendar")
                return
        except Exception as e:
            rumps.notification("AI Mail", "错误", str(e))
            self._finish_task("calendar")
            return

        def do_extract_and_add():
            try:
                rumps.notification("AI Mail", "🔄 AI 提取中", "正在分析邮件内容，请稍候...")

                # AI 提取信息
                info = ai_engine.extract_calendar_info(email)
                title = info.get("title", "") or email.get("subject", "无标题")
                notes = info.get("notes", "")

                if not title:
                    rumps.notification("AI Mail", "提示", "无法提取有效信息")
                    return

                rumps.notification(
                    title=f"✅ 已提取信息",
                    subtitle=f"标题：{title[:40]}",
                    message=f"备注：{notes[:100] if notes else '无'}\n\n请通过菜单栏「添加到日历/提醒」选择方式。"
                )
                # 暂时默认添加到提醒事项（日历需要交互选择）
                mail_reader.add_to_reminders(title, notes)

            except Exception as e:
                rumps.notification("AI Mail", "❌ 错误", str(e))
            finally:
                self._finish_task("calendar")

        threading.Thread(target=do_extract_and_add, daemon=True).start()

    @rumps.clicked("⚙️ 打开配置")
    def _open_config(self, _):
        """打开配置文件"""
        config_path = os.path.expanduser("~/.claude/scripts/ai-mail/config.json")
        if os.path.exists(config_path):
            subprocess.run(["open", config_path])
        else:
            rumps.notification("AI Mail", "提示", "配置文件不存在，请先运行安装脚本")

    @rumps.clicked("🚪 退出")
    def _quit_app(self, _):
        """退出应用"""
        rumps.quit_application()


def main():
    """主入口"""
    # 检查是否已运行
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("AI Mail 已在运行中，退出重复实例")
        sys.exit(0)

    try:
        app = AIMailApp()
        app.run()
    finally:
        release_lock(lock_fd)


if __name__ == "__main__":
    main()
