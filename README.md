# Stock Analysis Agent (股票分析智能体)

针对单只股票历史数据的 AI 股票操作决策智能体，基于 DeepSeek 大模型进行技术分析决策。

## 项目结构

```
si/
├── stock_agent.py          # 主程序：获取数据 & AI 分析
├── stock_indicator.txt     # 股票指标数据 & AI 分析结果
├── deepseek_apikey          # DeepSeek API 密钥（需用户配置）
├── test/
│   ├── backtest.py          # 历史数据回测脚本
│   ├── profitcal.py         # 回测盈亏计算
│   ├── backtest_report.txt  # 回测报告输出
│   └── incoming_data        # 回测用历史数据
└── README.md
```

## 核心功能

### 1. 实时股票分析 (`stock_agent.py`)

获取股票行情，发送给 DeepSeek AI 进行分析，输出交易建议。

**数据来源**：腾讯财经 API

**AI 模型支持**：
- `deepseek-chat` - 对话模型
- `deepseek-reasoner` - 推理模型（默认）

### 2. 历史回测 (`test/backtest.py`)

对历史行情进行模拟交易，验证 AI 策略有效性。

**回测流程**：
1. 逐日读取历史数据
2. 发送至 DeepSeek Reasoner 获取建议
3. 模拟执行买入/卖出/等待操作
4. 追踪持仓变化和资金余额

### 3. 盈亏计算 (`test/profitcal.py`)

根据回测报告计算最终收益率和资金曲线。

## 使用方法

### 环境要求

- Python 3.8+
- DeepSeek API Key

### 配置

1. 在项目根目录创建 `deepseek_apikey` 文件，写入你的 API 密钥

### 运行实时分析

```bash
python stock_agent.py
```

输出示例：
```
[2026-04-14 10:30:00] Stock Agent starting...
Fetching latest stock data...
Tencent API success: 2026-04-14,15.20,15.35,15.40,15.18,1250000,0.99
Querying DeepSeek for analysis...
DeepSeek suggestion: <Suggestion>买入 1000</Suggestion>
Done. Suggestion saved to stock_indicator.txt
```

### 运行回测

```bash
cd test
python backtest.py
python profitcal.py
```

## 数据格式

### 股票数据 (stock_indicator.txt)

```
<Date>{日期}</Date>
<Data>{日期},{开价},{当前价},{最高价},{最低价},{成交量},{涨跌幅}</Data>
<Suggestion>{AI分析建议}</Suggestion>
```

### 交易建议格式

- `<Suggestion>买入 {数量}</Suggestion>` - 买入指定数量
- `<Suggestion>卖出 {数量}</Suggestion>` - 卖出指定数量
- `<Suggestion>等待</Suggestion>` - 保持观望

## 注意事项

- 本项目仅供学习和研究之用
- 实际投资需自行承担风险
- API 调用有频率和成本限制
