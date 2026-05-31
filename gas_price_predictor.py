"""
gas_price_predictor.py - Ethereum Gas Price Predictor
By Rizal | github.com/rizalcodes
Predict optimal gas prices for Ethereum transactions
Multi-source: Etherscan Gas Oracle + Infura + Web3.py
Output: Real-time gas recommendations + Telegram alerts
"""

import os
import time
import logging
import requests
from web3 import Web3
from datetime import datetime
from collections import deque

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "Your_Etherscan_Api_Here")
INFURA_URL        = os.getenv("INFURA_URL",        "https://mainnet.infura.io/v3/Your_Infure_Key_Here")
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN",    "Your_Telegram_Bot_Token_Here")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID",  "1024188205")

# Alert thresholds (Gwei)
LOW_GAS_THRESHOLD  = 15   # alert kalau gas drop di bawah ini
HIGH_GAS_THRESHOLD = 100  # alert kalau gas spike di atas ini
POLL_INTERVAL      = 60   # cek setiap 60 detik

# TX cost estimates (gas units)
TX_GAS_UNITS = {
    "ETH Transfer"    : 21000,
    "ERC-20 Transfer" : 65000,
    "Uniswap Swap"    : 150000,
    "NFT Mint"        : 200000,
    "Contract Deploy" : 500000,
}


# ─────────────────────────────────────────────
# 1. GAS ORACLE CLIENT
# ─────────────────────────────────────────────
class GasOracleClient:
    """
    Multi-source gas price fetcher.
    Primary  : Etherscan Gas Oracle (most reliable)
    Fallback : Web3.py eth_gasPrice
    """
    ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"

    def __init__(self, api_key: str, infura_url: str):
        self.api_key = api_key
        self.w3      = Web3(Web3.HTTPProvider(infura_url))
        self.session = requests.Session()

    def get_gas_oracle(self) -> dict:
        """Ambil gas price dari Etherscan Gas Oracle."""
        try:
            r = self.session.get(
                self.ETHERSCAN_BASE,
                params={
                    "module" : "gastracker",
                    "action" : "gasoracle",
                    "apikey" : self.api_key,
                    "chainid": 1,
                },
                timeout=10
            )
            data   = r.json()
            result = data.get("result", {})
            if not result or isinstance(result, str):
                return {}
            return {
                "safe_gas"     : float(result.get("SafeGasPrice", 0)),
                "propose_gas"  : float(result.get("ProposeGasPrice", 0)),
                "fast_gas"     : float(result.get("FastGasPrice", 0)),
                "base_fee"     : float(result.get("suggestBaseFee", 0)),
                "gas_used_ratio": result.get("gasUsedRatio", ""),
                "source"       : "Etherscan",
                "timestamp"    : datetime.now().isoformat(),
            }
        except Exception as e:
            log.error(f"Etherscan gas oracle error: {e}")
            return {}

    def get_web3_gas(self) -> dict:
        """Fallback: ambil gas price dari Web3."""
        try:
            gas_price = self.w3.eth.gas_price
            gwei      = gas_price / 1e9
            block     = self.w3.eth.get_block("latest")
            base_fee  = int(block.get("baseFeePerGas", 0)) / 1e9

            return {
                "safe_gas"   : round(gwei * 0.9, 2),
                "propose_gas": round(gwei, 2),
                "fast_gas"   : round(gwei * 1.2, 2),
                "base_fee"   : round(base_fee, 2),
                "source"     : "Web3",
                "timestamp"  : datetime.now().isoformat(),
            }
        except Exception as e:
            log.error(f"Web3 gas error: {e}")
            return {}

    def get_gas(self) -> dict:
        """Get gas price — Etherscan first, Web3 fallback."""
        data = self.get_gas_oracle()
        if data and data.get("propose_gas", 0) > 0:
            return data
        log.warning("Etherscan failed, falling back to Web3...")
        return self.get_web3_gas()

    def get_eth_price(self) -> float:
        """Ambil ETH price buat kalkulasi USD cost."""
        try:
            r = self.session.get(
                self.ETHERSCAN_BASE,
                params={
                    "module" : "stats",
                    "action" : "ethprice",
                    "apikey" : self.api_key,
                    "chainid": 1,
                },
                timeout=10
            )
            result = r.json().get("result", {})
            return float(result.get("ethusd", 3000))
        except Exception:
            return 3000


# ─────────────────────────────────────────────
# 2. GAS PREDICTOR ENGINE
# ─────────────────────────────────────────────
class GasPredictor:
    """Core engine untuk predict & analyze gas prices."""

    def __init__(self, api_key: str, infura_url: str):
        self.oracle  = GasOracleClient(api_key, infura_url)
        self.history = deque(maxlen=60)  # keep last 60 readings (1 hour)
        self.alerts  = {
            "low_gas" : False,
            "high_gas": False,
        }

    def fetch(self) -> dict:
        """Fetch current gas + store to history."""
        data = self.oracle.get_gas()
        if data:
            self.history.append(data)
        return data

    def get_trend(self) -> dict:
        """Analyze gas price trend dari history."""
        if len(self.history) < 2:
            return {"trend": "UNKNOWN", "change_pct": 0, "direction": "➡️"}

        recent  = list(self.history)[-5:]   # last 5 readings
        older   = list(self.history)[:5]    # first 5 readings
        avg_recent = sum(r["propose_gas"] for r in recent) / len(recent)
        avg_older  = sum(r["propose_gas"] for r in older)  / len(older)

        if avg_older == 0:
            return {"trend": "UNKNOWN", "change_pct": 0, "direction": "➡️"}

        change_pct = ((avg_recent - avg_older) / avg_older) * 100

        if change_pct > 10:
            trend     = "RISING 📈"
            direction = "📈"
        elif change_pct < -10:
            trend     = "DROPPING 📉"
            direction = "📉"
        else:
            trend     = "STABLE ➡️"
            direction = "➡️"

        return {
            "trend"     : trend,
            "change_pct": round(change_pct, 2),
            "direction" : direction,
            "avg_recent": round(avg_recent, 2),
            "avg_older" : round(avg_older, 2),
        }

    def get_recommendation(self, gas_data: dict) -> dict:
        """Generate recommendation kapan dan berapa gas buat tx."""
        propose = gas_data.get("propose_gas", 0)
        safe    = gas_data.get("safe_gas", 0)
        fast    = gas_data.get("fast_gas", 0)
        trend   = self.get_trend()

        # Recommendation logic
        if propose <= LOW_GAS_THRESHOLD:
            timing = "🟢 GREAT TIME TO TRANSACT!"
            advice = "Gas is very low. Send transactions now!"
        elif propose <= 30:
            timing = "🟢 Good time to transact"
            advice = "Gas is reasonable. Safe to send transactions."
        elif propose <= 60:
            timing = "🟡 Moderate gas — consider waiting"
            advice = "Gas is moderate. Wait if not urgent."
        elif propose <= HIGH_GAS_THRESHOLD:
            timing = "🟠 High gas — wait if possible"
            advice = "Gas is high. Only send urgent transactions."
        else:
            timing = "🔴 VERY HIGH GAS — avoid if possible"
            advice = "Gas is extremely high. Wait for it to drop."

        # If dropping, add wait suggestion
        if "DROPPING" in trend["trend"] and propose > 30:
            advice += " Gas is dropping — wait a bit longer."

        return {
            "timing"  : timing,
            "advice"  : advice,
            "safe"    : safe,
            "propose" : propose,
            "fast"    : fast,
            "trend"   : trend,
        }

    def estimate_tx_cost(self, gas_price_gwei: float, eth_price: float) -> dict:
        """Estimate biaya setiap jenis transaksi."""
        costs = {}
        for tx_type, gas_units in TX_GAS_UNITS.items():
            cost_eth = (gas_price_gwei * gas_units) / 1e9
            cost_usd = cost_eth * eth_price
            costs[tx_type] = {
                "gas_units": gas_units,
                "cost_eth" : round(cost_eth, 6),
                "cost_usd" : round(cost_usd, 4),
            }
        return costs

    def check_alerts(self, gas_data: dict) -> list:
        """Check kalau ada alert condition."""
        propose = gas_data.get("propose_gas", 0)
        alerts  = []

        # Low gas alert
        if propose <= LOW_GAS_THRESHOLD and not self.alerts["low_gas"]:
            alerts.append({
                "type"   : "LOW_GAS",
                "gas"    : propose,
                "message": f"🟢 Gas is very low: *{propose} Gwei*\nGreat time to send transactions!",
            })
            self.alerts["low_gas"]  = True
            self.alerts["high_gas"] = False

        # High gas alert
        elif propose >= HIGH_GAS_THRESHOLD and not self.alerts["high_gas"]:
            alerts.append({
                "type"   : "HIGH_GAS",
                "gas"    : propose,
                "message": f"🔴 Gas spike detected: *{propose} Gwei*\nConsider waiting for gas to drop.",
            })
            self.alerts["high_gas"] = True
            self.alerts["low_gas"]  = False

        # Reset alerts when gas normalizes
        elif LOW_GAS_THRESHOLD < propose < HIGH_GAS_THRESHOLD:
            self.alerts["low_gas"]  = False
            self.alerts["high_gas"] = False

        return alerts

    def get_history_stats(self) -> dict:
        """Stats dari historical data."""
        if not self.history:
            return {}
        prices = [h["propose_gas"] for h in self.history]
        return {
            "readings"  : len(prices),
            "min_gwei"  : round(min(prices), 2),
            "max_gwei"  : round(max(prices), 2),
            "avg_gwei"  : round(sum(prices) / len(prices), 2),
            "current"   : round(prices[-1], 2),
            "period_min": len(prices),
        }


# ─────────────────────────────────────────────
# 3. TELEGRAM BOT
# ─────────────────────────────────────────────
class GasPredictorBot:
    def __init__(self):
        self.token      = TELEGRAM_TOKEN
        self.chat_id    = TELEGRAM_CHAT_ID
        self.base       = f"https://api.telegram.org/bot{self.token}"
        self.predictor  = GasPredictor(ETHERSCAN_API_KEY, INFURA_URL)
        self.offset     = 0
        self.running    = True
        self.monitoring = False
        log.info("🤖 GasPredictorBot initialized")

    def send(self, chat_id: str, text: str):
        for attempt in range(3):
            try:
                requests.post(
                    f"{self.base}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                    timeout=15
                )
                return
            except Exception as e:
                log.error(f"Send error (attempt {attempt+1}): {e}")
                time.sleep(2)

    def get_updates(self) -> list:
        try:
            r = requests.get(
                f"{self.base}/getUpdates",
                params={"offset": self.offset, "timeout": 10},
                timeout=15
            )
            return r.json().get("result", [])
        except Exception:
            return []

    def _format_gas(self, gas_data: dict, rec: dict, eth_price: float) -> str:
        """Format gas data untuk Telegram."""
        costs   = self.predictor.estimate_tx_cost(rec["propose"], eth_price)
        trend   = rec["trend"]
        propose = rec["propose"]
        source  = gas_data.get("source", "Unknown")

        msg = f"""
⛽ *GAS PRICE REPORT*
━━━━━━━━━━━━━━━━━━━━━━
🟢 Safe    : `{rec['safe']:.1f} Gwei` (~2 min)
🟡 Standard: `{rec['propose']:.1f} Gwei` (~30 sec)
🔴 Fast    : `{rec['fast']:.1f} Gwei` (~15 sec)
🏗️ Base Fee: `{gas_data.get('base_fee', 0):.1f} Gwei`

{rec['timing']}
💡 {rec['advice']}

📈 *Trend*: {trend['trend']} (`{trend['change_pct']:+.1f}%`)

💸 *TX Cost Estimates* (Standard gas):
        """.strip()

        for tx_type, cost in costs.items():
            msg += f"\n• {tx_type}: `${cost['cost_usd']:.2f}` (`{cost['cost_eth']:.6f} ETH`)"

        msg += f"\n\n📡 Source: `{source}`"
        msg += f"\n⏰ `{gas_data.get('timestamp', '')[:19]}`"
        return msg

    # ── Commands ──────────────────────────────
    def cmd_start(self, chat_id: str):
        self.send(chat_id, """
⛽ *Gas Price Predictor*
━━━━━━━━━━━━━━━━━━━━━━

Get optimal gas prices & TX cost estimates for Ethereum!

📋 *Commands:*
/gas — Current gas prices & recommendation
/fast — Fast gas price only
/estimate — TX cost calculator
/trend — Gas price trend analysis
/history — Historical stats
/alert — Set gas alert thresholds
/monitor on/off — Auto monitor & alerts
/help — Show commands
        """.strip())

    def cmd_gas(self, chat_id: str):
        self.send(chat_id, "⛽ Fetching gas prices...\n⏳ Please wait...")
        try:
            gas_data  = self.predictor.fetch()
            if not gas_data:
                self.send(chat_id, "❌ Could not fetch gas data. Try again later.")
                return
            eth_price = self.predictor.oracle.get_eth_price()
            rec       = self.predictor.get_recommendation(gas_data)
            self.send(chat_id, self._format_gas(gas_data, rec, eth_price))
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    def cmd_fast(self, chat_id: str):
        try:
            gas_data = self.predictor.fetch()
            if not gas_data:
                self.send(chat_id, "❌ Could not fetch gas data.")
                return
            fast    = gas_data.get("fast_gas", 0)
            propose = gas_data.get("propose_gas", 0)
            safe    = gas_data.get("safe_gas", 0)
            self.send(chat_id, f"⛽ *Quick Gas Check*\n━━━━━━━━━━━━━━━━━━━━━━\n🟢 Safe    : `{safe:.1f} Gwei`\n🟡 Standard: `{propose:.1f} Gwei`\n🔴 Fast    : `{fast:.1f} Gwei`\n\n⏰ `{datetime.now().strftime('%H:%M:%S')}`")
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    def cmd_estimate(self, chat_id: str, args: list):
        try:
            gas_data  = self.predictor.fetch()
            if not gas_data:
                self.send(chat_id, "❌ Could not fetch gas data.")
                return
            eth_price = self.predictor.oracle.get_eth_price()

            # Use standard gas if no arg, else use provided gwei
            if args and args[0].replace(".", "").isdigit():
                gwei = float(args[0])
            else:
                gwei = gas_data.get("propose_gas", 30)

            costs = self.predictor.estimate_tx_cost(gwei, eth_price)
            msg   = f"💸 *TX Cost Estimates @ {gwei} Gwei*\n━━━━━━━━━━━━━━━━━━━━━━\n💰 ETH Price: `${eth_price:,.2f}`\n\n"
            for tx_type, cost in costs.items():
                msg += f"• *{tx_type}*\n  `{cost['gas_units']:,}` gas → `${cost['cost_usd']:.4f}` (`{cost['cost_eth']:.6f} ETH`)\n\n"
            msg += f"⏰ `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            self.send(chat_id, msg)
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    def cmd_trend(self, chat_id: str):
        # Fetch a few readings if history is empty
        if len(self.predictor.history) < 3:
            self.send(chat_id, "🔄 Collecting data...\n⏳ Please wait ~10 seconds...")
            for _ in range(3):
                self.predictor.fetch()
                time.sleep(3)

        trend = self.predictor.get_trend()
        stats = self.predictor.get_history_stats()

        if not stats:
            self.send(chat_id, "❌ Not enough data yet. Try again in a minute.")
            return

        self.send(chat_id, f"""
📈 *GAS TREND ANALYSIS*
━━━━━━━━━━━━━━━━━━━━━━
{trend['direction']} Trend      : *{trend['trend']}*
📊 Change     : `{trend['change_pct']:+.2f}%`
🕐 Recent Avg : `{trend['avg_recent']} Gwei`
🕐 Older Avg  : `{trend['avg_older']} Gwei`

📉 *Session Stats ({stats['period_min']} min)*
- Min  : `{stats['min_gwei']} Gwei`
- Max  : `{stats['max_gwei']} Gwei`
- Avg  : `{stats['avg_gwei']} Gwei`
- Now  : `{stats['current']} Gwei`

⏰ `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
        """.strip())

    def cmd_history(self, chat_id: str):
        stats = self.predictor.get_history_stats()
        if not stats:
            self.send(chat_id, "📭 No history yet.\nUse /gas first to start collecting data.")
            return

        # Show last 5 readings
        recent = list(self.predictor.history)[-5:]
        msg    = f"📊 *Gas Price History*\n━━━━━━━━━━━━━━━━━━━━━━\n📈 Min : `{stats['min_gwei']} Gwei`\n📉 Max : `{stats['max_gwei']} Gwei`\n📊 Avg : `{stats['avg_gwei']} Gwei`\n🔢 Readings: `{stats['readings']}`\n\n*Last 5 Readings:*\n"
        for r in reversed(recent):
            ts   = r.get("timestamp", "")[:19]
            gwei = r.get("propose_gas", 0)
            msg += f"• `{gwei:.1f} Gwei` — `{ts}`\n"
        self.send(chat_id, msg)

    def cmd_alert(self, chat_id: str, args: list):
        global LOW_GAS_THRESHOLD, HIGH_GAS_THRESHOLD
        if not args:
            self.send(chat_id, f"🔔 *Alert Thresholds*\n━━━━━━━━━━━━━━━━━━━━━━\n🟢 Low alert  : `{LOW_GAS_THRESHOLD} Gwei`\n🔴 High alert : `{HIGH_GAS_THRESHOLD} Gwei`\n\nSet: `/alert low <gwei>` or `/alert high <gwei>`")
            return
        if len(args) >= 2 and args[1].isdigit():
            val = int(args[1])
            if args[0].lower() == "low":
                LOW_GAS_THRESHOLD = val
                self.send(chat_id, f"✅ Low gas alert set to `{val} Gwei`")
            elif args[0].lower() == "high":
                HIGH_GAS_THRESHOLD = val
                self.send(chat_id, f"✅ High gas alert set to `{val} Gwei`")
        else:
            self.send(chat_id, "⚠️ Usage: `/alert low 15` or `/alert high 100`")

    def cmd_monitor(self, chat_id: str, args: list):
        if not args:
            status = "ON ✅" if self.monitoring else "OFF ❌"
            self.send(chat_id, f"📡 Gas Monitor: *{status}*\nUse `/monitor on` or `/monitor off`\n\n🔔 Alert when:\n• Gas < `{LOW_GAS_THRESHOLD} Gwei` (low)\n• Gas > `{HIGH_GAS_THRESHOLD} Gwei` (high)")
            return
        if args[0].lower() == "on":
            self.monitoring = True
            self.send(chat_id, f"✅ *Gas Monitor ON*\nChecking every {POLL_INTERVAL}s.\n🔔 Alerts: low < `{LOW_GAS_THRESHOLD}` | high > `{HIGH_GAS_THRESHOLD}` Gwei")
        elif args[0].lower() == "off":
            self.monitoring = False
            self.send(chat_id, "❌ *Gas Monitor OFF*")

    # ── Message Router ────────────────────────
    def handle(self, message: dict):
        text    = message.get("text", "").strip()
        chat_id = str(message.get("chat", {}).get("id", ""))
        if not text or not chat_id:
            return
        parts   = text.split()
        command = parts[0].lower()
        args    = parts[1:]
        log.info(f"📨 {command} from {chat_id}")

        if command in ("/start", "/help"): self.cmd_start(chat_id)
        elif command == "/gas":            self.cmd_gas(chat_id)
        elif command == "/fast":           self.cmd_fast(chat_id)
        elif command == "/estimate":       self.cmd_estimate(chat_id, args)
        elif command == "/trend":          self.cmd_trend(chat_id)
        elif command == "/history":        self.cmd_history(chat_id)
        elif command == "/alert":          self.cmd_alert(chat_id, args)
        elif command == "/monitor":        self.cmd_monitor(chat_id, args)
        else:
            self.send(chat_id, "❓ Unknown command. Type /help for commands.")

    # ── Background Monitor ────────────────────
    def _monitor_loop(self):
        log.info("⛽ Gas monitor loop started")
        while self.running:
            try:
                gas_data = self.predictor.fetch()
                if gas_data and self.monitoring:
                    alerts = self.predictor.check_alerts(gas_data)
                    for alert in alerts:
                        self.send(self.chat_id, f"⛽ *GAS ALERT*\n━━━━━━━━━━━━━━━━━━━━━━\n{alert['message']}\n\n⏰ `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
                        log.info(f"🔔 Alert sent: {alert['type']} — {alert['gas']} Gwei")
            except Exception as e:
                log.error(f"Monitor loop error: {e}")
            time.sleep(POLL_INTERVAL)

    # ── Main Loop ─────────────────────────────
    def run(self):
        import threading
        log.info("🚀 GasPredictorBot started!")
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        while self.running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    if msg:
                        self.handle(msg)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                log.error(f"Polling error: {e}")
                time.sleep(5)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        predictor = GasPredictor(ETHERSCAN_API_KEY, INFURA_URL)
        print("\n⛽ Fetching gas prices...")
        gas_data  = predictor.fetch()
        eth_price = predictor.oracle.get_eth_price()

        if not gas_data:
            print("❌ Could not fetch gas data.")
            sys.exit(1)

        print(f"\n🟢 Safe    : {gas_data['safe_gas']:.1f} Gwei")
        print(f"🟡 Standard: {gas_data['propose_gas']:.1f} Gwei")
        print(f"🔴 Fast    : {gas_data['fast_gas']:.1f} Gwei")
        print(f"🏗️ Base Fee: {gas_data['base_fee']:.1f} Gwei")
        print(f"📡 Source  : {gas_data['source']}")
        print(f"💰 ETH     : ${eth_price:,.2f}")

        rec   = predictor.get_recommendation(gas_data)
        costs = predictor.estimate_tx_cost(gas_data["propose_gas"], eth_price)
        print(f"\n{rec['timing']}")
        print(f"💡 {rec['advice']}")
        print(f"\n💸 TX Cost Estimates:")
        for tx_type, cost in costs.items():
            print(f"  • {tx_type}: ${cost['cost_usd']:.4f} ({cost['cost_eth']:.6f} ETH)")
    else:
        bot = GasPredictorBot()
        bot.run()