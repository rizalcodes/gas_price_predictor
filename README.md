# ⛽ Gas Price Predictor

> Real-time Ethereum gas price recommendations & TX cost estimates with Telegram alerts — powered by Etherscan Gas Oracle + Web3.py.

![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)
![Etherscan](https://img.shields.io/badge/Etherscan-Gas_Oracle-21325b?style=flat-square)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram)
![Ethereum](https://img.shields.io/badge/Ethereum-Mainnet-627EEA?style=flat-square&logo=ethereum)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🔍 What is Gas Price Prediction?

Ethereum gas prices fluctuate constantly based on network demand. Paying too much wastes money — paying too little means your transaction gets stuck. This bot monitors gas in real-time and tells you exactly when and how much to pay.

This bot fetches gas data using:
- 📋 **Etherscan Gas Oracle** — primary source, most reliable
- ⛓️ **Web3.py + Infura** — fallback when Etherscan is unavailable
- 💰 **Etherscan ETH Price API** — for USD cost calculation

---

## ✨ Features

- ⛽ **Real-time Gas Prices** — Safe, Standard & Fast in Gwei
- 💸 **TX Cost Estimates** — USD cost for 5 common transaction types
- 📈 **Trend Analysis** — detect if gas is rising, dropping or stable
- 🔔 **Spike & Drop Alerts** — get notified when gas hits thresholds
- 📊 **Session History** — track min/max/avg over time
- ⚙️ **Custom Thresholds** — set your own low/high alert levels
- 📡 **Auto Monitor** — background polling every 60 seconds
- 🤖 **Telegram Bot** — 7 interactive commands

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install web3 requests
```

### 2. Set API keys

Open `gas_price_predictor.py` and configure:

```python
ETHERSCAN_API_KEY = "your_etherscan_key"
INFURA_URL        = "https://mainnet.infura.io/v3/your_infura_key"
TELEGRAM_TOKEN    = "your_telegram_bot_token"
TELEGRAM_CHAT_ID  = "your_chat_id"
```

### 3. Run as Telegram Bot

```bash
python gas_price_predictor.py
```

### 4. Quick CLI check (one-time)

```bash
python gas_price_predictor.py check
```

---

## 🤖 Telegram Commands

| Command | Description |
|---------|-------------|
| `/gas` | Full gas report + TX cost estimates |
| `/fast` | Quick gas check (Safe/Standard/Fast) |
| `/estimate <gwei>` | TX cost at custom gas price |
| `/trend` | Gas price trend analysis |
| `/history` | Session min/max/avg stats |
| `/alert low <gwei>` | Set low gas alert threshold |
| `/alert high <gwei>` | Set high gas alert threshold |
| `/monitor on/off` | Toggle auto monitoring & alerts |

---

## 📊 Sample Output

```
⛽ GAS PRICE REPORT
━━━━━━━━━━━━━━━━━━━━━━
🟢 Safe    : 0.1 Gwei  (~2 min)
🟡 Standard: 0.1 Gwei  (~30 sec)
🔴 Fast    : 0.1 Gwei  (~15 sec)
🏗️ Base Fee: 0.1 Gwei

🟢 GREAT TIME TO TRANSACT!
💡 Gas is very low. Send transactions now!

📈 Trend: STABLE ➡️ (+0.94%)

💸 TX Cost Estimates (Standard gas):
- ETH Transfer    : $0.00 (0.000002 ETH)
- ERC-20 Transfer : $0.01 (0.000006 ETH)
- Uniswap Swap    : $0.04 (0.000019 ETH)
- NFT Mint        : $0.05 (0.000026 ETH)
- Contract Deploy : $0.13 (0.000064 ETH)

📡 Source: Etherscan
⏰ 2026-05-31T20:13:28
```

---

## 🚨 Alert System

| Alert | Trigger | Description |
|-------|---------|-------------|
| 🟢 Low Gas | Gas drops below threshold | Great time to transact |
| 🔴 High Gas | Gas spikes above threshold | Consider waiting |

Default thresholds: Low = `15 Gwei` / High = `100 Gwei`

Customize with `/alert low 10` or `/alert high 80`.

---

## 🏗️ Architecture

```
gas_price_predictor.py
├── GasOracleClient     → Multi-source gas price fetcher
│   ├── get_gas_oracle()     → Etherscan Gas Oracle (primary)
│   ├── get_web3_gas()       → Web3.py via Infura (fallback)
│   ├── get_gas()            → Auto-select best source
│   └── get_eth_price()      → ETH/USD via Etherscan
├── GasPredictor        → Core prediction engine
│   ├── fetch()              → Fetch + store to history
│   ├── get_trend()          → Analyze rising/dropping/stable
│   ├── get_recommendation() → When & how much to pay
│   ├── estimate_tx_cost()   → USD cost per TX type
│   ├── check_alerts()       → Detect spike/drop conditions
│   └── get_history_stats()  → Session min/max/avg
└── GasPredictorBot     → Telegram bot with 7 commands
    └── _monitor_loop()      → Background polling thread
```

---

## 📡 Data Sources

| Source | Usage |
|--------|-------|
| [Etherscan Gas Oracle](https://etherscan.io/gastracker) | Primary — Safe/Standard/Fast/BaseFee |
| [Web3.py + Infura](https://infura.io) | Fallback gas price |
| [Etherscan ETH Price](https://etherscan.io) | ETH/USD conversion |

---

## 💸 TX Cost Reference

| Transaction Type | Gas Units | Description |
|-----------------|-----------|-------------|
| ETH Transfer | 21,000 | Simple ETH send |
| ERC-20 Transfer | 65,000 | Token transfer |
| Uniswap Swap | 150,000 | DEX swap |
| NFT Mint | 200,000 | Mint NFT |
| Contract Deploy | 500,000 | Deploy smart contract |

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOW_GAS_THRESHOLD` | 15 Gwei | Alert when gas drops below |
| `HIGH_GAS_THRESHOLD` | 100 Gwei | Alert when gas spikes above |
| `POLL_INTERVAL` | 60s | How often to check gas |

---

## ⚠️ Disclaimer

> **Gas prices change every block (~12 seconds). This tool provides recommendations based on current network conditions — always verify before sending high-value transactions.**

---

## 🔧 Requirements

```
web3>=6.0.0
requests>=2.28.0
```

---

## 👤 Author

**Rizal** — [@rizalcodes](https://github.com/rizalcodes)

> Building Web3 tools with Python 🐍⛓️

---

## 📄 License

MIT License — free to use, modify, and distribute.
