#!/usr/bin/env python3
"""Apple Mail 读写模块 - 通过 AppleScript 操作 Mail.app"""

import subprocess
import json
import re


def run_applescript(script):
    """执行 AppleScript 并返回结果"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}")
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"AppleScript exception: {e}")
        return None


def get_unread_count():
    """获取收件箱未读邮件数（只扫描最近100封，避免超时）"""
    script = '''
    tell application "Mail"
        set unreadCount to 0
        set allMsgs to messages of mailbox "INBOX" of account 1
        set totalMsgs to count of allMsgs
        set scanLimit to totalMsgs
        if scanLimit > 20 then set scanLimit to 20
        repeat with i from 1 to scanLimit
            if read status of (item i of allMsgs) is false then
                set unreadCount to unreadCount + 1
            end if
        end repeat
        return unreadCount
    end tell
    '''
    result = run_applescript(script)
    try:
        return int(result) if result else 0
    except ValueError:
        return 0


def get_unread_emails(max_count=20, folders=None):
    """获取未读邮件列表（支持多个文件夹）"""
    if folders is None:
        folders = ["INBOX"]

    all_emails = []

    for folder in folders:
        # 使用遍历方式查找文件夹，避免直接引用导致的编码问题
        script = f'''
        tell application "Mail"
            set emailList to {{}}
            set mailboxList to every mailbox of account 1
            set foundFolder to false

            repeat with mb in mailboxList
                set mbName to name of mb
                if mbName is "{folder}" then
                    set foundFolder to true
                    try
                        set allMsgs to messages of mb
                        set totalMsgs to count of allMsgs
                        set scanLimit to totalMsgs
                        if scanLimit > 20 then set scanLimit to 20
                        set checked to 0
                        repeat with i from 1 to scanLimit
                            if checked >= {max_count} then exit repeat
                            set msg to item i of allMsgs
                            if read status of msg is false then
                                set senderName to sender of msg
                                set subjectText to subject of msg
                                set dateText to date received of msg as string
                                set bodyText to ""
                                try
                                    set bodyText to content of msg
                                    if length of bodyText > 800 then
                                        set bodyText to text 1 thru 800 of bodyText
                                    end if
                                    -- 替换换行为空格，避免破坏解析
                                    set AppleScript's text item delimiters to return
                                    set bodyTextParts to text items of bodyText
                                    set AppleScript's text item delimiters to space
                                    set bodyText to bodyTextParts as string
                                    set AppleScript's text item delimiters to linefeed
                                    set bodyTextParts to text items of bodyText
                                    set AppleScript's text item delimiters to space
                                    set bodyText to bodyTextParts as string
                                    set AppleScript's text item delimiters to ""
                                end try
                                set end of emailList to "SENDER:" & senderName & "|||SUBJECT:" & subjectText & "|||DATE:" & dateText & "|||BODY:" & bodyText & "|||END"
                                set checked to checked + 1
                            end if
                        end repeat
                        set AppleScript's text item delimiters to linefeed
                        return emailList as string
                    on error
                        return ""
                    end try
                end if
            end repeat

            if not foundFolder then
                return ""
            end if
        end tell
        '''
        result = run_applescript(script)
        if not result:
            continue

        for line in result.split("\n"):
            line = line.strip()
            if not line or "|||END" not in line:
                continue
            parts = line.split("|||")
            email = {}
            for part in parts:
                if part.startswith("SENDER:"):
                    email["sender"] = part[7:]
                elif part.startswith("SUBJECT:"):
                    email["subject"] = part[8:]
                elif part.startswith("DATE:"):
                    email["date"] = part[5:]
                elif part.startswith("BODY:"):
                    email["body"] = part[5:]
            if email.get("sender"):
                all_emails.append(email)

    return all_emails


def get_selected_email():
    """获取 Mail.app 当前选中的邮件"""
    script = '''
    tell application "Mail"
        set selectedMsgs to selected messages of message viewer 1
        if (count of selectedMsgs) = 0 then return "NO_SELECTION"
        set msg to item 1 of selectedMsgs
        set senderName to sender of msg
        set subjectText to subject of msg
        set dateText to date received of msg as string
        set bodyText to ""
        try
            set bodyText to content of msg
            if length of bodyText > 1000 then
                set bodyText to text 1 thru 1000 of bodyText
            end if
        end try
        return "SENDER:" & senderName & "|||SUBJECT:" & subjectText & "|||DATE:" & dateText & "|||BODY:" & bodyText
    end tell
    '''
    result = run_applescript(script)
    if not result or result == "NO_SELECTION":
        return None

    email = {}
    for part in result.split("|||"):
        if part.startswith("SENDER:"):
            email["sender"] = part[7:]
        elif part.startswith("SUBJECT:"):
            email["subject"] = part[8:]
        elif part.startswith("DATE:"):
            email["date"] = part[5:]
        elif part.startswith("BODY:"):
            email["body"] = part[5:]
    return email if email.get("sender") else None


def mark_all_read():
    """标记收件箱所有邮件为已读"""
    script = '''
    tell application "Mail"
        set inboxMessages to messages of mailbox "INBOX" of account 1
        repeat with msg in inboxMessages
            set read status of msg to true
        end repeat
    end tell
    '''
    result = run_applescript(script)
    return result is not None


def create_draft(to_addr="", subject="", body=""):
    """在 Apple Mail 创建草稿"""
    # 转义特殊字符
    subject = subject.replace('"', '\\"')
    body = body.replace('"', '\\"')
    to_addr = to_addr.replace('"', '\\"')

    script = f'''
    tell application "Mail"
        set newMsg to make new outgoing message with properties {{visible:true, subject:"{subject}", content:"{body}"}}
        tell newMsg
            make new to recipient at end of to recipients with properties {{address:"{to_addr}"}}
        end tell
    end tell
    '''
    result = run_applescript(script)
    return result is not None


def reply_to_email(email, reply_body):
    """回复选中的邮件"""
    subject = email.get("subject", "")
    sender = email.get("sender", "")
    reply_body = reply_body.replace('"', '\\"')
    subject = subject.replace('"', '\\"')

    # 提取发件人邮箱地址
    email_match = re.search(r'<(.+?)>', sender)
    addr = email_match.group(1) if email_match else sender

    script = f'''
    tell application "Mail"
        set newMsg to make new outgoing message with properties {{visible:true, subject:"Re: {subject}", content:"{reply_body}"}}
        tell newMsg
            make new to recipient at end of to recipients with properties {{address:"{addr}"}}
        end tell
    end tell
    '''
    result = run_applescript(script)
    return result is not None


def add_to_calendar(title, start_date, notes=""):
    """添加到 macOS 日历"""
    title = title.replace('"', '\\"')
    notes = notes.replace('"', '\\"')

    script = f'''
    tell application "Calendar"
        tell calendar "日历"
            set startDate to current date
            set endDate to startDate + 1 * hours
            make new event with properties {{summary:"{title}", description:"{notes}", start date:startDate, end date:endDate}}
        end tell
    end tell
    '''
    result = run_applescript(script)
    return result is not None


def add_to_reminders(title, notes="", due_date=""):
    """添加到 macOS 提醒事项"""
    title = title.replace('"', '\\"')
    notes = notes.replace('"', '\\"')

    script = f'''
    tell application "Reminders"
        set listCount to count of lists
        if listCount = 0 then
            make new list with properties {{name:"提醒事项"}}
        end if
        tell list 1
            make new reminder at end with properties {{name:"{title}", body:"{notes}"}}
        end tell
    end tell
    '''
    result = run_applescript(script)
    return result is not None


def count_emails_from_sender(sender_pattern, folders=None):
    """统计来自指定发件人的邮件数量（包括已读和未读）"""
    if folders is None:
        folders = ["INBOX"]

    total_count = 0

    for folder in folders:
        sender_pattern_escaped = sender_pattern.replace('"', '\\"')

        script = f'''
        tell application "Mail"
            set matchCount to 0
            set mailboxList to every mailbox of account 1

            repeat with mb in mailboxList
                set mbName to name of mb
                if mbName is "{folder}" then
                    set allMsgs to messages of mb
                    set totalMsgs to count of allMsgs
                    set scanLimit to totalMsgs
                    if scanLimit > 500 then set scanLimit to 500

                    repeat with i from 1 to scanLimit
                        set msg to item i of allMsgs
                        set senderAddr to sender of msg
                        if senderAddr contains "{sender_pattern_escaped}" then
                            set matchCount to matchCount + 1
                        end if
                    end repeat
                end if
            end repeat
            return matchCount
        end tell
        '''
        result = run_applescript(script)
        try:
            total_count += int(result) if result else 0
        except ValueError:
            pass

    return total_count


def delete_emails_from_sender(sender_pattern, folders=None):
    """删除来自指定发件人的邮件（包括已读和未读）"""
    if folders is None:
        folders = ["INBOX"]

    total_deleted = 0

    for folder in folders:
        # 转义特殊字符
        sender_pattern_escaped = sender_pattern.replace('"', '\\"')

        # 使用倒序遍历删除，避免索引变化问题
        script = f'''
        tell application "Mail"
            set deletedCount to 0
            set mailboxList to every mailbox of account 1

            repeat with mb in mailboxList
                set mbName to name of mb
                if mbName is "{folder}" then
                    set allMsgs to messages of mb
                    set totalMsgs to count of allMsgs
                    set scanLimit to totalMsgs
                    if scanLimit > 500 then set scanLimit to 500

                    -- 倒序遍历
                    repeat with i from scanLimit to 1 by -1
                        set msg to item i of allMsgs
                        set senderAddr to sender of msg
                        if senderAddr contains "{sender_pattern_escaped}" then
                            delete msg
                            set deletedCount to deletedCount + 1
                        end if
                    end repeat
                end if
            end repeat
            return deletedCount
        end tell
        '''
        result = run_applescript(script)
        try:
            deleted = int(result) if result else 0
            total_deleted += deleted
        except ValueError:
            pass

    return total_deleted
