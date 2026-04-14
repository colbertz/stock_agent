#!/usr/bin/env python3
"""
Backtest script for stock 000027 Shenzhen Energy.
Iterates through 2025 data day by day:
1. Insert one day's data
2. Query DeepSeek reasoner for suggestion
3. Execute action at next day's open price
4. Track positions and compute final P&L
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime

# ==== Config ====
WORKSPACE = "./"
SI_FILE = os.path.join(WORKSPACE, "si_test")
INCOMING_FILE = os.path.join(WORKSPACE, "incoming_data")
APIKEY_FILE = "deepseek_apikey"
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-reasoner"
INITIAL_QUOTA = 60000
# 回测配置
MAX_TRADE_DAYS = 243 

# ==== Helper Functions ====

def read_api_key():
    with open(APIKEY_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def load_incoming_data(incoming_file):
    """Load 2025 simulation data from incoming_data file."""
    with open(incoming_file, "r", encoding="utf-8") as f:
        lines = f.read().strip().split('\n')
    return lines

def split_si_content(content):
    """Split si file content at <UserMessage> into system_prompt and user_message.
    <UserMessage> line itself belongs to the user_message section.
    """
    lines = content.strip().split('\n')
    system_lines = []
    user_lines = []
    user_message_started = False
    for line in lines:
        if line.startswith('<UserMessage>'):
            user_message_started = True
        if user_message_started:
            user_lines.append(line)
        else:
            system_lines.append(line)
    return "\n".join(system_lines).strip(), "\n".join(user_lines).strip()

def query_deepseek(system_prompt, user_message, api_key):
    """Send prompt to DeepSeek and get suggestion."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.3
    }

    req = urllib.request.Request(
        DEEPSEEK_API,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            message = result['choices'][0]['message']

            thinking = message.get('reasoning_content', '')
            content_resp = message.get('content', '')

            if thinking:
                print(f"  [Reasoner thought]: {thinking}")
            print(f"  [DeepSeek response]: {content_resp}")

            return content_resp
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error: {e.code} - {e.read().decode()}")
        return None
    except Exception as e:
        print(f"  Request Error: {e}")
        return None

def parse_suggestion(response):
    """Parse suggestion from DeepSeek response.
    response couble be three possible actions in the following format
    <Suggestion>等待</Suggestion>
    <Suggestion>买入 数量</Suggestion>
    <Suggestion>卖出 数量</Suggestion>
    this function will return a tuple (action, quantity)
    """
    if not response:
        return None, 0
    match = re.search(r'<Suggestion>(.*?)</Suggestion>', response)
    if match:
        suggestion = match.group(1).strip()
        if suggestion == "等待":
            return "等待", 0
        elif suggestion.startswith("买入"):
            qty_match = re.search(r'买入\s+(\d+)', suggestion)
            if qty_match:
                return "买入", int(qty_match.group(1))
        elif suggestion.startswith("卖出"):
            qty_match = re.search(r'卖出\s+(\d+)', suggestion)
            if qty_match:
                return "卖出", int(qty_match.group(1))
    return None, 0

def build_userstock(last_userstock, action, quantity):
    """Build new <UserStock> tag content based on last_userstock, action and quantity."""
    # Parse last_userstock
    match = re.search(r'持有(\d+)\s+剩余仓位(\d+)', last_userstock)
    if match:
        current_holding = int(match.group(1))
        remaining_quota = int(match.group(2))
    else:
        current_holding = 0
        remaining_quota = INITIAL_QUOTA

    # Update based on action
    if action == "等待":
        return last_userstock
    elif action == "买入":
        current_holding += quantity
        remaining_quota -= quantity
    elif action == "卖出":
        current_holding -= quantity
        remaining_quota += quantity
    
    return f"<UserStock>持有{current_holding} 剩余仓位{remaining_quota}</UserStock>"    

def run_backtest():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Backtest starting...")

    # Load si_test content and split into system prompt + user message template
    with open(SI_FILE, "r", encoding="utf-8") as f:
        si_content = f.read()
    system_prompt, user_msg = split_si_content(si_content)

    incoming_list = load_incoming_data(INCOMING_FILE)
    api_key = read_api_key()

    print(f"2025 trading days: {len(incoming_list)}")

    total_days = min(len(incoming_list), MAX_TRADE_DAYS)
    actual_incoming = incoming_list[:total_days]

    report_loc = len(user_msg)
    last_userstock = "<UserStock>持有0 剩余仓位60000</UserStock>"  # 初始持仓状态
    user_msg += '\n' + last_userstock  # 将初始持仓状态加入user_msg

    for i in range(total_days):
        today_data_line = actual_incoming[i]
        print(f"\n--- Day {i+1}/{total_days}: {today_data_line} ---")
        #step1 append <Data>{today_data_line}</Data> as a new line at the end of user_msg
        user_msg = user_msg + f'\n<Data>{today_data_line}</Data>'

        #step2 send system_prompt and user_msg to DeepSeek and get suggestion
        response = query_deepseek(system_prompt, user_msg, api_key)
        user_msg += '\n' + response

        #step3 parse suggestion to get action and quantity
        action, quantity = parse_suggestion(response)
        last_userstock = build_userstock(last_userstock, action, quantity)
        user_msg += '\n' + last_userstock
    
    #after the loop, let's write the final user_msg from report_loc to a file for analysis
    with open("backtest_report.txt", "w", encoding="utf-8") as f:
        f.write(user_msg[report_loc:])

if __name__ == "__main__":
    run_backtest()
