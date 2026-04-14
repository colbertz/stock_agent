#!/usr/bin/env python3
"""
Stock Analysis Agent for 000027 深圳能源
- Fetches latest daily data and appends to stock_indicator.txt
- Sends data to DeepSeek for analysis
- Updates file with suggestion
"""

import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# ==== Config ====
WORKSPACE = "./"
SI_FILE = os.path.join(WORKSPACE, "stock_indicator.txt")
APIKEY_FILE = os.path.join(WORKSPACE, "deepseek_apikey")
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"

# Model type: "chat" for deepseek-chat, "reasoner" for deepseek-reasoner
MODEL_TYPE = "reasoner"  # <-- 修改这里来切换模型: "chat" 或 "reasoner"

# Map MODEL_TYPE to actual model name
MODEL_MAP = {
    "chat": "deepseek-chat",
    "reasoner": "deepseek-reasoner"
}
MODEL = MODEL_MAP[MODEL_TYPE]

# ==== Helper Functions ====

def get_latest_data():
    return get_tencent_data()


def get_tencent_data():
    """Fetch data from Tencent Finance API"""
    import urllib.request
    
    url = "https://qt.gtimg.cn/q=sz000027"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://finance.qq.com'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('gbk')
            
            # Format: v_sz000027="51~name~code~current~yesterday_close~open~volume~..."
            match = re.search(r'v_sz000027="([^"]+)"', data)
            if not match:
                return None, None
            
            parts = match.group(1).split('~')
            
            # parts[1]=name, parts[2]=code, parts[3]=current, parts[4]=yesterday_close
            # parts[5]=open, parts[33]=high, parts[34]=low, parts[36]=volume (in 100 shares)
            # parts[30]=date like 20260413
            
            current_price = float(parts[3])
            yesterday_close = float(parts[4])
            open_price = float(parts[5]) if parts[5] else current_price
            high = float(parts[33]) if parts[33] else current_price
            low = float(parts[34]) if parts[34] else current_price
            volume = int(parts[36]) * 100 if parts[36] else 0  # Tencent volume is in 100 shares
            
            date_str = parts[30]  # Format: YYYYMMDD
            # Convert to YYYY-MM-DD
            date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            
            change_pct = round((current_price - yesterday_close) / yesterday_close * 100, 2)
            
            data_line = f"{date_str},{open_price},{current_price},{high},{low},{volume},{change_pct}"
            print(f"Tencent API success: {data_line}")
            return date_str, data_line
            
    except Exception as e:
        print(f"Tencent API failed: {e}")
        return None, None


def read_api_key():
    """Read DeepSeek API key"""
    with open(APIKEY_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def query_deepseek(content, api_key):
    """Send content to DeepSeek and get suggestion"""
    
    # Build the prompt - extract system prompt from si file and user content
    lines = content.strip().split('\n')
    
    # 在lines中找到<UserMessage>标签，之前的行为system prompt，之后的行为user message
    system_lines = []
    user_lines = []
    user_message_started = False    
    for line in lines:
        if line.startswith('<UserMessage>'):
            user_message_started = True
            continue
        if user_message_started:
            user_lines.append(line)
        else:
            system_lines.append(line)
    system_prompt = "\n".join(system_lines).strip()
    user_message = "\n".join(user_lines).strip()
    
    # Make API request
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

            # For deepseek-reasoner, the response may contain a 'thinking' field
            # The actual answer is in 'content'
            thinking = message.get('reasoning_content', '')
            content = message.get('content', '')

            if thinking and MODEL_TYPE == "reasoner":
                print(f"[Reasoner thought process]: {thinking}...")
                #output thinking content to log under folder logs using filename YYYYMMDD
                log_folder = os.path.join(WORKSPACE, "logs")
                os.makedirs(log_folder, exist_ok=True)
                log_file = os.path.join(log_folder, datetime.now().strftime("%Y%m%d") + ".log")
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[Reasoner thought process]: {thinking}...\n")

            return content
        
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")
        return None
    except Exception as e:
        print(f"Request Error: {e}")
        return None


def parse_suggestion(response):
    """Extract suggestion from DeepSeek response"""
    if not response:
        return None
    
    match = re.search(r'<Suggestion>\s*(.*?)\s*</Suggestion>', response)
    if match:
        return match.group(1).strip()
    
    # Fallback: try to find buy/sell/wait
    if '买入' in response:
        return response
    elif '卖出' in response:
        return response
    elif '等待' in response:
        return response
    
    return response.strip()


def update_si_file(data_line, suggestion):
    """Append Data and Suggestion to si file"""
    with open(SI_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Remove existing <Data> tag if it has the same date (to avoid duplicates on re-run)
    date_str = data_line.split(',')[0]
    
    # Remove incomplete Data-Suggestion pair (Data without matching Suggestion)
    # Find the last Data tag and check if it has a Suggestion after it
    last_data_idx = content.rfind('<Data>')
    last_suggestion_idx = content.rfind('<Suggestion>')
    last_UserStock_idx = content.rfind('<UserStock>')
    
    # If last Data is after last Suggestion and last UserStock, remove it
    if last_data_idx > last_suggestion_idx and last_data_idx > last_UserStock_idx:
        # Find the \n before this Data tag
        content_before = content[:last_data_idx]
        # Find the last newline before Data
        newline_idx = content_before.rfind('\n')
        content = content_before[:newline_idx] + '\n'
    
    # Append new Data and Suggestion
    content = content.rstrip() + f'\n<Data>{data_line}</Data>\n'
    if suggestion:
        content += f'<Suggestion>{suggestion}</Suggestion>\n'
    
    with open(SI_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    return True


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Stock Agent starting...")
    
    # Step 1: Get latest data
    print("Fetching latest stock data...")
    date_str, data_line = get_latest_data()
    
    if not data_line:
        print("Failed to fetch stock data")
        return
    
    print(f"Latest data: {data_line}")
    
    # Step 2: Read API key
    api_key = read_api_key()
    
    # Step 3: Read current si file content
    with open(SI_FILE, "r", encoding="utf-8") as f:
        si_content = f.read()
    
    # Step 4: Update si file with new Data tag
    # First save without suggestion so we can send full context
    update_si_file(data_line, None)
    
    # Step 5: Query DeepSeek
    print("Querying DeepSeek for analysis...")
    
    # Re-read after update
    with open(SI_FILE, "r", encoding="utf-8") as f:
        updated_content = f.read()
    
    suggestion_response = query_deepseek(updated_content, api_key)
    
    if not suggestion_response:
        print("Failed to get suggestion from DeepSeek")
        return

    suggestion = parse_suggestion(suggestion_response)
    print(f"DeepSeek suggestion: {suggestion}")

    # Step 6: Update si file with suggestion
    update_si_file(data_line, suggestion)
    print("Done. Suggestion saved to stock_indicator.txt")


if __name__ == "__main__":
    main()
