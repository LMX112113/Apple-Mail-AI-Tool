#!/usr/bin/env python3
"""AI 引擎模块 - 调用 Claude API"""

import json
import os
import re


def get_api_config():
    """读取 API 配置"""
    config_path = os.path.expanduser("~/.claude/scripts/ai-mail/config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("api", {})


def get_filter_config():
    """读取过滤配置"""
    config_path = os.path.expanduser("~/.claude/scripts/ai-mail/config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("filter", {})


def get_mail_config():
    """读取邮件配置"""
    config_path = os.path.expanduser("~/.claude/scripts/ai-mail/config.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("mail", {})


def call_claude(prompt, system_prompt="", max_tokens=None):
    """调用 Claude API"""
    try:
        from anthropic import Anthropic
    except ImportError:
        return "错误：未安装 anthropic，请运行 pip install anthropic"

    api_config = get_api_config()

    # 优先使用配置文件的 api_key，其次环境变量
    api_key = api_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    base_url = api_config.get("base_url") or os.environ.get("ANTHROPIC_BASE_URL")

    if not api_key:
        return "错误：未配置 API key，请在 config.json 或环境变量 ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN 中设置"

    model = api_config.get("model", "claude-sonnet-4-20250514")
    if max_tokens is None:
        max_tokens = api_config.get("max_tokens", 2000)

    try:
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        client = Anthropic(**kwargs)
        msg_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            msg_kwargs["system"] = system_prompt

        response = client.messages.create(**msg_kwargs)
        # 处理 thinking 模型（可能有 ThinkingBlock + TextBlock）
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        return "\n".join(text_parts) if text_parts else str(response.content[0])
    except Exception as e:
        return f"API 调用失败：{str(e)}"


def filter_emails(emails):
    """根据过滤规则筛选邮件，返回 (正常总结的邮件, 仅统计的邮件)"""
    filter_config = get_filter_config()
    count_only_rules = filter_config.get("count_only_rules", [])
    exclude_rules = filter_config.get("exclude_rules", [])
    include_rules = filter_config.get("include_rules", [])

    normal_emails = []  # 正常总结的邮件
    count_only_emails = []  # 仅统计的邮件

    for email in emails:
        sender = email.get("sender", "")
        subject = email.get("subject", "")

        # 先检查排除规则
        excluded = False
        for rule in exclude_rules:
            field_val = sender if rule["field"] == "sender" else subject
            if re.search(rule["contains"], field_val, re.IGNORECASE):
                excluded = True
                break
        if excluded:
            continue

        # 检查仅统计规则
        count_only = False
        for rule in count_only_rules:
            field_val = sender if rule["field"] == "sender" else subject
            if re.search(rule["contains"], field_val, re.IGNORECASE):
                count_only = True
                break
        if count_only:
            count_only_emails.append(email)
            continue

        # 检查包含规则
        included = False
        for rule in include_rules:
            field_val = sender if rule["field"] == "sender" else subject
            if re.search(rule["contains"], field_val, re.IGNORECASE):
                included = True
                break
        if included:
            normal_emails.append(email)

    return normal_emails, count_only_emails


def summarize_emails(normal_emails, count_only_emails=None):
    """AI 总结邮件（按发件人分组）+ 仅统计邮件"""
    if count_only_emails is None:
        count_only_emails = []

    if not normal_emails and not count_only_emails:
        return "没有需要总结的未读邮件。"

    filter_config = get_filter_config()
    custom_prompt = filter_config.get("custom_prompt", "请用中文简洁总结以下邮件，提取关键信息和待办事项。")

    # 构建统计部分
    count_summary = ""
    if count_only_emails:
        # 按发件人分组统计
        count_grouped = {}
        for email in count_only_emails:
            sender = email.get('sender', '未知')
            name_match = re.match(r'^"?([^"<]+)"?\s*(?:<|$)', sender)
            sender_name = name_match.group(1).strip() if name_match else sender
            count_grouped[sender_name] = count_grouped.get(sender_name, 0) + 1

        count_lines = []
        for sender_name, count in sorted(count_grouped.items(), key=lambda x: -x[1]):
            count_lines.append(f"- {sender_name}：{count}封")
        count_summary = f"\n## 📊 仅统计（{len(count_only_emails)}封）\n" + "\n".join(count_lines) + "\n"

    # 如果没有需要正常总结的邮件，直接返回统计
    if not normal_emails:
        return f"✅ 没有需要详细总结的邮件\n{count_summary}"

    # 按发件人分组正常邮件
    grouped = {}
    for email in normal_emails:
        sender = email.get('sender', '未知')
        name_match = re.match(r'^"?([^"<]+)"?\s*(?:<|$)', sender)
        sender_name = name_match.group(1).strip() if name_match else sender
        if sender_name not in grouped:
            grouped[sender_name] = []
        grouped[sender_name].append(email)

    # 构建分组格式化的邮件内容
    email_texts = []
    for sender_name, sender_emails in grouped.items():
        email_texts.append(f"\n\n{'='*60}\n【{sender_name}】({len(sender_emails)}封)\n{'='*60}")
        for i, email in enumerate(sender_emails, 1):
            body = email.get('body', '无内容')
            if len(body) > 800:
                body = body[:800] + "..."
            text = f"\n{i}. 主题：{email.get('subject', '无主题')}\n   时间：{email.get('date', '未知')}\n   内容：\n{body}\n"
            email_texts.append(text)

    prompt = f"""{custom_prompt}

以下是按发件人分组的未读邮件：

{''.join(email_texts)}

**输出要求（严格遵守）：**
1. 只按发件人分组，总结每组的邮件内容
2. 格式：**发件人名称**（X封）+ 邮件内容总结
3. **禁止输出**：待办事项、紧急程度、优先级、行动建议或任何其他章节
4. **禁止使用**：📋、🚨、🔴、🟡、🟢 等图标
5. 只输出 📧 未读邮件总结 这一个章节，不要其他任何内容

示例格式：
## 📧 未读邮件总结

**张三**（2封）
- 会议通知：明天下午3点开会
- 项目进度：本周完成80%

**李四**（1封）
- 报销审批：已通过"""

    ai_summary = call_claude(prompt, system_prompt="你是一个专业的邮件分析助手。只按发件人分组总结邮件内容，简洁明了，不要列出待办事项、紧急程度或任何其他额外信息。")

    # 后处理：删除 AI 可能生成的多余章节
    lines = ai_summary.split('\n')
    cleaned_lines = []
    skip_until_next_header = False

    for line in lines:
        # 检测到这些章节标题（## 开头）
        if line.startswith('## '):
            # 如果是不要的章节，开始跳过
            if any(keyword in line for keyword in ['待办事项', '紧急程度', '优先级', '行动建议']):
                skip_until_next_header = True
                continue
            # 如果是 📊 仅统计，保留
            elif '仅统计' in line:
                skip_until_next_header = False
                cleaned_lines.append(line)
                continue
            # 其他 ## 标题（如 📧 未读邮件总结），保留并停止跳过
            else:
                skip_until_next_header = False
                cleaned_lines.append(line)
                continue

        # 如果正在跳过章节，跳过这一行
        if skip_until_next_header:
            continue

        # 跳过 📋、🚨 开头的行
        if line.strip().startswith('📋') or line.strip().startswith('🚨'):
            continue

        # 跳过 🔴、🟡、🟢 开头的行
        if any(line.strip().startswith(emoji) for emoji in ['🔴', '🟡', '🟢']):
            continue

        cleaned_lines.append(line)

    ai_summary = '\n'.join(cleaned_lines).strip()

    # 组合 AI 总结和统计
    full_summary = ai_summary + "\n" + count_summary if count_summary else ai_summary
    return full_summary


def compose_email(subject_hint, key_points):
    """AI 写邮件"""
    prompt = f"请根据以下信息帮我写一封邮件：\n主题方向：{subject_hint}\n要点：{key_points}\n\n请输出邮件的主题和正文，格式：\n主题：xxx\n正文：xxx\n\n邮件末尾签名固定为：姓名"

    result = call_claude(prompt, system_prompt="你是一个专业的邮件撰写助手，请用中文写出格式规范、语气得体的邮件。邮件末尾必须有签名：姓名")

    # 解析主题和正文
    subject = ""
    body = ""
    lines = result.split("\n")
    in_body = False
    for line in lines:
        if line.startswith("主题：") or line.startswith("主题:"):
            subject = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        elif line.startswith("正文：") or line.startswith("正文:"):
            in_body = True
            body = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        elif in_body:
            body += "\n" + line

    # 确保签名存在
    if "姓名" not in body:
        body += "\n\n姓名"

    return subject.strip(), body.strip(), result


def generate_reply(email):
    """AI 生成回复"""
    prompt = f"请帮我回复以下邮件：\n\n发件人：{email.get('sender', '')}\n主题：{email.get('subject', '')}\n内容：{email.get('body', '')}\n\n请输出回复内容，语气得体专业。"

    return call_claude(prompt, system_prompt="你是一个专业的邮件回复助手，请用中文写出得体的回复。")


def extract_calendar_info(email):
    """从邮件中提取日历/提醒事项信息"""
    prompt = f"""请从以下邮件中提取可以添加到日历或提醒事项的信息。

发件人：{email.get('sender', '')}
主题：{email.get('subject', '')}
内容：{email.get('body', '')}

请按 JSON 格式输出：
{{
  "title": "事项标题",
  "notes": "备注信息",
  "type": "calendar" 或 "reminder",
  "date_hint": "日期时间提示（如有）"
}}

如果没有可提取的信息，返回 {{"title": "", "notes": "", "type": "", "date_hint": ""}}"""

    result = call_claude(prompt, system_prompt="你是一个信息提取助手，请从邮件中提取日历/提醒事项信息，只输出 JSON。")

    try:
        # 提取 JSON
        json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    return {"title": email.get("subject", ""), "notes": "", "type": "reminder", "date_hint": ""}
