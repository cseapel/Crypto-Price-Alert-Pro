import json
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_COINS = {
    "BTC (Bitcoin)": "bitcoin",
    "ETH (Ethereum)": "ethereum",
    "BNB (BNB)": "binancecoin",
    "SOL (Solana)": "solana",
    "ADA (Cardano)": "cardano",
    "XRP (XRP)": "ripple",
    "DOGE (Dogecoin)": "dogecoin",
    "MATIC (Polygon)": "matic-network",
    "AVAX (Avalanche)": "avalanche-2",
    "DOT (Polkadot)": "polkadot",
    "LINK (Chainlink)": "chainlink",
    "TRX (Tron)": "tron",
    "TON (Toncoin)": "the-open-network",
    "NEAR (Near Protocol)": "near",
    "ATOM (Cosmos)": "cosmos",
    "LTC (Litecoin)": "litecoin",
    "BCH (Bitcoin Cash)": "bitcoin-cash",
    "ETC (Ethereum Classic)": "ethereum-classic",
    "ARB (Arbitrum)": "arbitrum",
    "OP (Optimism)": "optimism",
    "SUI (Sui)": "sui",
    "APT (Aptos)": "aptos",
    "SEI (Sei)": "sei-network",
    "SHIB (Shiba Inu)": "shiba-inu",
    "PEPE (Pepe)": "pepe",
    "ONDO (Ondo)": "ondo-finance",
}

VS_CURRENCIES = ["usd", "aud"]

ENTRY_ZONES = {
    "SOL (Solana)": {
        "usd": {"good_min": 75.0, "good_max": 80.0, "strong_min": 65.0, "strong_max": 70.0},
        "aud": {"good_min": 110.0, "good_max": 120.0, "strong_min": 95.0, "strong_max": 105.0},
    },
    "ADA (Cardano)": {
        "usd": {"good_min": 0.20, "good_max": 0.22, "strong_min": 0.15, "strong_max": 0.18},
        "aud": {"good_min": 0.30, "good_max": 0.33, "strong_min": 0.22, "strong_max": 0.27},
    },
    "XRP (XRP)": {
        "usd": {"good_min": 0.45, "good_max": 0.50, "strong_min": 0.35, "strong_max": 0.40},
        "aud": {"good_min": 0.70, "good_max": 0.75, "strong_min": 0.55, "strong_max": 0.65},
    },
    "ONDO (Ondo)": {
        "usd": {"good_min": 0.60, "good_max": 0.70, "strong_min": 0.40, "strong_max": 0.50},
        "aud": {"good_min": 0.90, "good_max": 1.05, "strong_min": 0.60, "strong_max": 0.75},
    },
}

CAUTION_LEVELS = {
    "SOL (Solana)": {"usd": 95.0, "aud": 145.0},
    "ADA (Cardano)": {"usd": 0.30, "aud": 0.45},
    "XRP (XRP)": {"usd": 0.70, "aud": 1.05},
    "ONDO (Ondo)": {"usd": 1.00, "aud": 1.50},
}

TARGET_TOLERANCE = 0.03
PRICE_CACHE_TTL = 20
HISTORY_CACHE_TTL = 300
TOP_COINS_CACHE_TTL = 900
RATE_LIMIT_COOLDOWN = 90


class PriceAlertApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Crypto Price Alert Pro")
        self.root.configure(bg="#f5f7fb")

        self.running = False
        self.worker = None
        self.alarm_running = False
        self.last_price = None
        self.last_alert_key = None
        self.coins = dict(DEFAULT_COINS)
        self.filtered_coin_names = list(self.coins.keys())

        self.coin_var = tk.StringVar(value="SOL (Solana)")
        self.search_var = tk.StringVar(value="")
        self.currency_var = tk.StringVar(value="aud")
        self.target_var = tk.StringVar(value="120")
        self.direction_var = tk.StringVar(value="below")
        self.interval_var = tk.StringVar(value="60")

        self.current_price_var = tk.StringVar(value="Current price: -")
        self.status_var = tk.StringVar(value="Status: Idle")
        self.strategy_var = tk.StringVar(value="Strategy view: Click Check Now to get a live suggestion")
        self.signal_var = tk.StringVar(value="WAIT")

        self.price_cache = {}
        self.history_cache = {}
        self.top_coins_cache = None
        self.rate_limited_until = 0.0

        self._setup_style()
        self._build_ui()
        self.center_window()

    def _setup_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg = "#f5f7fb"
        card = "#ffffff"
        text = "#111827"
        muted = "#6b7280"
        border = "#dbe2ea"
        accent = "#2563eb"

        style.configure("App.TFrame", background=bg)
        style.configure("Card.TFrame", background=card, relief="flat")
        style.configure("Card.TLabelframe", background=card, borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", background=card, foreground=text, font=("Segoe UI", 11, "bold"))

        style.configure("App.TLabel", background=bg, foreground=text, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=card, foreground=text, font=("Segoe UI", 10))
        style.configure("Value.TLabel", background=card, foreground=text, font=("Segoe UI", 11, "bold"))
        style.configure("Signal.TLabel", background=card, foreground=accent, font=("Segoe UI", 26, "bold"))

        style.configure(
            "App.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 10),
        )
        style.map(
            "App.TButton",
            background=[("active", "#dbeafe")],
        )

        style.configure("App.TEntry", padding=8)
        style.configure("App.TCombobox", padding=8)

        self.colors = {
            "bg": bg,
            "card": card,
            "text": text,
            "muted": muted,
            "border": border,
            "accent": accent,
            "green": "#16a34a",
            "amber": "#d97706",
            "red": "#dc2626",
        }

    def center_window(self) -> None:
        width = 980
        height = 720
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(900, 680)

    def _build_ui(self) -> None:
        self.main = ttk.Frame(self.root, style="App.TFrame", padding=18)
        self.main.pack(fill="both", expand=True)

        header = ttk.Frame(self.main, style="App.TFrame")
        header.pack(fill="x", pady=(0, 14))

        ttk.Label(
            header,
            text="Crypto Price Alert Pro",
            style="App.TLabel",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Live crypto price alerts with cleaner UI, caching, smart signals, and working alarm test.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(self.main, style="App.TFrame")
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content, style="App.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right = ttk.Frame(content, style="App.TFrame")
        right.pack(side="left", fill="both", expand=True)

        settings_card = ttk.LabelFrame(left, text="Alert Settings", style="Card.TLabelframe", padding=16)
        settings_card.pack(fill="x", pady=(0, 12))

        self._add_labeled_input(settings_card, "Search coin", 0)
        search_entry = ttk.Entry(settings_card, textvariable=self.search_var, style="App.TEntry")
        search_entry.grid(row=0, column=1, sticky="ew", pady=6)
        search_entry.bind("<KeyRelease>", self.on_search_change)

        ttk.Label(settings_card, text="Coin", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 12))
        self.coin_combo = ttk.Combobox(
            settings_card,
            textvariable=self.coin_var,
            values=self.filtered_coin_names,
            state="readonly",
            style="App.TCombobox",
        )
        self.coin_combo.grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(settings_card, text="Currency", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Combobox(
            settings_card,
            textvariable=self.currency_var,
            values=VS_CURRENCIES,
            state="readonly",
            style="App.TCombobox",
        ).grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Label(settings_card, text="Target price", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Entry(settings_card, textvariable=self.target_var, style="App.TEntry").grid(row=3, column=1, sticky="ew", pady=6)

        ttk.Label(settings_card, text="Alert when price is", style="Card.TLabel").grid(row=4, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Combobox(
            settings_card,
            textvariable=self.direction_var,
            values=["above", "below"],
            state="readonly",
            style="App.TCombobox",
        ).grid(row=4, column=1, sticky="ew", pady=6)

        ttk.Label(settings_card, text="Check interval (sec)", style="Card.TLabel").grid(row=5, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Entry(settings_card, textvariable=self.interval_var, style="App.TEntry").grid(row=5, column=1, sticky="ew", pady=6)

        settings_card.columnconfigure(1, weight=1)

        button_card = ttk.LabelFrame(left, text="Actions", style="Card.TLabelframe", padding=16)
        button_card.pack(fill="x", pady=(0, 12))

        row1 = ttk.Frame(button_card, style="Card.TFrame")
        row1.pack(fill="x", pady=(0, 8))
        ttk.Button(row1, text="Load Top 100", style="App.TButton", command=self.load_top_coins).pack(side="left")
        ttk.Button(row1, text="Check Now", style="App.TButton", command=self.check_now).pack(side="left", padx=8)
        ttk.Button(row1, text="Start Alert", style="App.TButton", command=self.start_alert).pack(side="left")

        row2 = ttk.Frame(button_card, style="Card.TFrame")
        row2.pack(fill="x")
        ttk.Button(row2, text="Stop", style="App.TButton", command=self.stop_alert).pack(side="left")
        ttk.Button(row2, text="Test Alarm", style="App.TButton", command=self.test_alarm).pack(side="left", padx=8)

        signal_card = ttk.LabelFrame(right, text="Live Signal", style="Card.TLabelframe", padding=18)
        signal_card.pack(fill="both", expand=True, pady=(0, 12))

        self.signal_label = ttk.Label(signal_card, textvariable=self.signal_var, style="Signal.TLabel")
        self.signal_label.pack(anchor="w")

        ttk.Label(signal_card, textvariable=self.current_price_var, style="Value.TLabel").pack(anchor="w", pady=(8, 6))
        ttk.Label(signal_card, textvariable=self.status_var, style="Card.TLabel", wraplength=400).pack(anchor="w", pady=(0, 8))
        ttk.Label(signal_card, textvariable=self.strategy_var, style="Card.TLabel", wraplength=400, justify="left").pack(anchor="w")

        notes_card = ttk.LabelFrame(right, text="Notes", style="Card.TLabelframe", padding=18)
        notes_card.pack(fill="both", expand=True)

        notes = (
            "• Live prices and price history come from CoinGecko.\n"
            "• Load Top 100 fetches popular coins once and then caches the result.\n"
            "• The app cools down automatically if the API rate limit is hit.\n"
            "• Test Alarm lets you verify sound without waiting for a live trigger.\n"
            "• Saved entry zones improve suggestions for SOL, ADA, XRP and ONDO.\n"
            "• This is educational only, not financial advice."
        )
        ttk.Label(notes_card, text=notes, style="Card.TLabel", wraplength=400, justify="left").pack(anchor="w")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _add_labeled_input(self, parent, text: str, row: int) -> None:
        ttk.Label(parent, text=text, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))

    def _now(self) -> float:
        return time.time()

    def _is_rate_limited(self) -> bool:
        return self._now() < self.rate_limited_until

    def _seconds_until_retry(self) -> int:
        return max(0, int(self.rate_limited_until - self._now()))

    def _set_rate_limit(self, seconds: int = RATE_LIMIT_COOLDOWN) -> None:
        self.rate_limited_until = self._now() + seconds

    def _fetch_json(self, url: str, timeout: int = 20):
        if self._is_rate_limited():
            raise RuntimeError(f"Rate limited. Retry in {self._seconds_until_retry()}s")

        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429:
                self._set_rate_limit()
                raise RuntimeError(f"Rate limited by CoinGecko. Retry in {self._seconds_until_retry()}s") from exc
            raise

    def on_search_change(self, event=None) -> None:
        term = self.search_var.get().strip().lower()
        if not term:
            self.filtered_coin_names = list(self.coins.keys())
        else:
            self.filtered_coin_names = [name for name in self.coins.keys() if term in name.lower()]
        self.coin_combo["values"] = self.filtered_coin_names
        if self.filtered_coin_names and self.coin_var.get() not in self.filtered_coin_names:
            self.coin_var.set(self.filtered_coin_names[0])
        elif not self.filtered_coin_names:
            self.coin_var.set("")

    def get_top_coins(self, limit: int = 100) -> dict:
        cache_key = f"top_{limit}"
        now = self._now()
        if (
            self.top_coins_cache
            and self.top_coins_cache.get("key") == cache_key
            and now - self.top_coins_cache.get("time", 0) < TOP_COINS_CACHE_TTL
        ):
            return dict(self.top_coins_cache["data"])

        url = (
            "https://api.coingecko.com/api/v3/coins/markets"
            f"?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
        )
        data = self._fetch_json(url, timeout=20)

        coins = {}
        for item in data:
            symbol = str(item.get("symbol", "")).upper()
            name = str(item.get("name", "")).strip()
            coin_id = str(item.get("id", "")).strip()
            if symbol and name and coin_id:
                coins[f"{symbol} ({name})"] = coin_id

        self.top_coins_cache = {"key": cache_key, "time": now, "data": dict(coins)}
        return coins

    def load_top_coins(self) -> None:
        try:
            self.status_var.set("Status: Loading top coins...")
            live_coins = self.get_top_coins(100)
            self.coins = live_coins if live_coins else dict(DEFAULT_COINS)
            self.on_search_change()
            self.status_var.set(f"Status: Loaded {len(self.coins)} popular coins")
        except RuntimeError as exc:
            self.coins = dict(DEFAULT_COINS)
            self.on_search_change()
            self.status_var.set(f"Status: {exc}")
        except Exception as exc:
            self.coins = dict(DEFAULT_COINS)
            self.on_search_change()
            self.status_var.set(f"Status: Could not load top coins, using default list: {exc}")
            messagebox.showwarning(
                "Top coins unavailable",
                f"Could not load the Top 100 right now.\n\nUsing the built-in list instead.\n\n{exc}",
            )

    def get_price(self, coin_id: str, currency: str) -> float:
        cache_key = (coin_id, currency)
        now = self._now()
        cached = self.price_cache.get(cache_key)
        if cached and now - cached["time"] < PRICE_CACHE_TTL:
            return float(cached["value"])

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={currency}"
        data = self._fetch_json(url, timeout=15)
        value = float(data[coin_id][currency])
        self.price_cache[cache_key] = {"time": now, "value": value}
        return value

    def get_market_chart(self, coin_id: str, currency: str, days: int = 14) -> list[float]:
        cache_key = (coin_id, currency, days)
        now = self._now()
        cached = self.history_cache.get(cache_key)
        if cached and now - cached["time"] < HISTORY_CACHE_TTL:
            return list(cached["value"])

        url = (
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            f"?vs_currency={currency}&days={days}&interval=daily"
        )
        data = self._fetch_json(url, timeout=20)
        prices = [float(point[1]) for point in data.get("prices", [])]
        if not prices:
            raise ValueError("No historical price data returned")
        self.history_cache[cache_key] = {"time": now, "value": list(prices)}
        return prices

    def simple_rsi(self, prices: list[float], period: int = 7):
        if len(prices) <= period:
            return None

        gains = []
        losses = []
        recent = prices[-(period + 1):]

        for i in range(1, len(recent)):
            diff = recent[i] - recent[i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(diff))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def get_signal_label(self, zone_state: str, live_state: str) -> str:
        if zone_state in {"strong_buy", "good_buy"} and live_state in {"dip_buy", "staged_buy"}:
            return "BUY"
        if live_state == "overheated" or zone_state == "caution":
            return "WAIT"
        if live_state == "weak_bounce":
            return "WAIT"
        if zone_state == "below_strong":
            return "WATCH"
        return "WAIT"

    def _set_signal_color(self, signal: str) -> None:
        if signal == "BUY":
            self.signal_label.configure(foreground=self.colors["green"])
        elif signal == "WATCH":
            self.signal_label.configure(foreground=self.colors["amber"])
        else:
            self.signal_label.configure(foreground=self.colors["red"])

    def get_strategy_text(self, coin_name: str, currency: str, price: float, target: float = None) -> str:
        zones = ENTRY_ZONES.get(coin_name, {}).get(currency)
        if not zones:
            coin_id = self.coins.get(coin_name)
            live_state = "mixed"
            live_text = "Live signal unavailable right now."

            if coin_id:
                try:
                    history = self.get_market_chart(coin_id, currency, days=14)
                    if len(history) >= 10:
                        sma5 = sum(history[-5:]) / 5
                        sma10 = sum(history[-10:]) / 10
                        rsi7 = self.simple_rsi(history, period=7)
                        trend = "uptrend" if sma5 > sma10 else "downtrend"

                        if rsi7 is None:
                            live_state = "mixed"
                            live_text = f"Live signal: {trend}, momentum unavailable."
                        elif rsi7 < 35 and price <= sma5:
                            live_state = "dip_buy"
                            live_text = f"Live signal: possible dip-buy area. Trend={trend}, RSI7={rsi7:.1f}."
                        elif rsi7 > 68 and price >= sma5:
                            live_state = "overheated"
                            live_text = f"Live signal: overheated, wait for pullback. Trend={trend}, RSI7={rsi7:.1f}."
                        elif sma5 > sma10 and price <= sma5 * 1.02:
                            live_state = "staged_buy"
                            live_text = f"Live signal: healthy uptrend, okay for staged buying. RSI7={rsi7:.1f}."
                        elif sma5 < sma10 and price > sma5:
                            live_state = "weak_bounce"
                            live_text = f"Live signal: bounce inside weaker trend, better to stay patient. RSI7={rsi7:.1f}."
                        else:
                            live_state = "mixed"
                            live_text = f"Live signal: mixed market, consider DCA only. RSI7={rsi7:.1f}."
                except Exception:
                    live_text = "Live signal unavailable right now."

            if live_state in {"dip_buy", "staged_buy"}:
                signal = "BUY"
            elif live_state in {"overheated", "weak_bounce"}:
                signal = "WAIT"
            else:
                signal = "WATCH"

            self.signal_var.set(signal)
            self._set_signal_color(signal)

            base = f"Strategy view: Full live mode for this coin. No saved zone yet. {live_text}"
            if target is not None:
                base += " Your target will be monitored live against current market conditions."
            return base

        coin_id = self.coins.get(coin_name)
        strong_min = zones["strong_min"]
        strong_max = zones["strong_max"]
        good_min = zones["good_min"]
        good_max = zones["good_max"]
        caution_level = CAUTION_LEVELS.get(coin_name, {}).get(currency)

        if strong_min <= price <= strong_max:
            zone_state = "strong_buy"
            zone_text = f"Strong buy zone. Price is inside {strong_min} to {strong_max} {currency.upper()}"
        elif good_min <= price <= good_max:
            zone_state = "good_buy"
            zone_text = f"Good accumulation zone. Price is inside {good_min} to {good_max} {currency.upper()}"
        elif price < strong_min:
            zone_state = "below_strong"
            zone_text = "Below strong zone. Very cheap area, but falling momentum can be risky"
        elif caution_level is not None and price >= caution_level:
            zone_state = "caution"
            zone_text = "Not ideal to chase right now. Price looks extended versus the planned entry zone"
        else:
            zone_state = "neutral"
            zone_text = (
                f"Neutral area. Better to wait for dips toward {good_min}-{good_max} or "
                f"{strong_min}-{strong_max} {currency.upper()}"
            )

        live_state = "mixed"
        live_text = "Live signal unavailable right now."

        if coin_id:
            try:
                history = self.get_market_chart(coin_id, currency, days=14)
                if len(history) >= 10:
                    sma5 = sum(history[-5:]) / 5
                    sma10 = sum(history[-10:]) / 10
                    rsi7 = self.simple_rsi(history, period=7)
                    trend = "uptrend" if sma5 > sma10 else "downtrend"

                    if rsi7 is None:
                        live_state = "mixed"
                        live_text = f"Live signal: {trend}, momentum unavailable."
                    elif rsi7 < 35 and price <= sma5:
                        live_state = "dip_buy"
                        live_text = f"Live signal: possible dip-buy area. Trend={trend}, RSI7={rsi7:.1f}."
                    elif rsi7 > 68 and price >= sma5:
                        live_state = "overheated"
                        live_text = f"Live signal: overheated, wait for pullback. Trend={trend}, RSI7={rsi7:.1f}."
                    elif sma5 > sma10 and price <= sma5 * 1.02:
                        live_state = "staged_buy"
                        live_text = f"Live signal: healthy uptrend, okay for staged buying. RSI7={rsi7:.1f}."
                    elif sma5 < sma10 and price > sma5:
                        live_state = "weak_bounce"
                        live_text = f"Live signal: bounce inside weaker trend, better to stay patient. RSI7={rsi7:.1f}."
                    else:
                        live_state = "mixed"
                        live_text = f"Live signal: mixed market, consider DCA only. RSI7={rsi7:.1f}."
            except Exception:
                live_state = "mixed"
                live_text = "Live signal unavailable right now."

        signal = self.get_signal_label(zone_state, live_state)
        self.signal_var.set(signal)
        self._set_signal_color(signal)

        base = f"Strategy view: {zone_text}. {live_text}"

        if target is not None:
            lower_bound = good_min * (1 - TARGET_TOLERANCE)
            upper_bound = caution_level if caution_level is not None else good_max * (1 + TARGET_TOLERANCE)

            if target < lower_bound:
                target_note = " Your target is very low, so it may take time to reach."
            elif (good_min <= target <= good_max) or (strong_min <= target <= strong_max):
                target_note = " Your target sits in one of the planned buy zones."
            elif caution_level is not None and target >= upper_bound:
                target_note = " Your target is high relative to the planned entry zone, so that would be more of a breakout or chasing entry."
            else:
                target_note = " Your target is between neutral and buy-zone levels."
            base += target_note

        return base

    def play_alarm(self) -> None:
        self.alarm_running = True
        for _ in range(15):
            if not self.alarm_running:
                break
            try:
                import winsound
                winsound.Beep(1200, 350)
            except Exception:
                try:
                    self.root.bell()
                except Exception:
                    pass
            time.sleep(0.15)
        self.alarm_running = False

    def test_alarm(self) -> None:
        if not self.alarm_running:
            threading.Thread(target=self.play_alarm, daemon=True).start()
            self.status_var.set("Status: Alarm test running")

    def check_now(self) -> None:
        try:
            coin_name = self.coin_var.get()
            coin_id = self.coins[coin_name]
            currency = self.currency_var.get().lower()
            target = float(self.target_var.get())

            price = self.get_price(coin_id, currency)
            self.last_price = price
            self.current_price_var.set(f"Current price: {price:.8f} {currency.upper()}")
            self.strategy_var.set(self.get_strategy_text(coin_name, currency, price, target))
            self.status_var.set("Status: Price fetched successfully")
            self._check_alert_condition(coin_name, coin_id, currency, price, target)
        except ValueError:
            messagebox.showerror("Invalid input", "Target price must be a valid number.")
        except KeyError:
            messagebox.showerror("Invalid input", "Please choose a valid coin.")
        except RuntimeError as exc:
            self.status_var.set(f"Status: {exc}")
            self.strategy_var.set(
                "Strategy view: API rate limit hit. App is cooling down automatically and will work again after the wait."
            )
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            self.status_var.set(f"Status: Failed to fetch price: {exc}")
            messagebox.showerror("Network error", f"Could not fetch price.\n\n{exc}")

    def start_alert(self) -> None:
        if self.running:
            self.status_var.set("Status: Alert already running")
            return

        try:
            float(self.target_var.get())
            interval = int(self.interval_var.get())
            if interval < 5:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid settings", "Target price must be a number and interval must be at least 5 seconds.")
            return

        self.running = True
        self.status_var.set("Status: Monitoring started")
        self.check_now()
        self.worker = threading.Thread(target=self._monitor_loop, daemon=True)
        self.worker.start()

    def stop_alert(self) -> None:
        self.running = False
        self.alarm_running = False
        self.status_var.set("Status: Monitoring stopped")

    def _check_alert_condition(self, coin_name: str, coin_id: str, currency: str, price: float, target: float) -> None:
        direction = self.direction_var.get().lower()
        hit = (direction == "above" and price >= target) or (direction == "below" and price <= target)
        alert_key = (coin_id, currency, target, direction)

        if hit and self.last_alert_key != alert_key:
            self.last_alert_key = alert_key
            self._show_alert(coin_name, price, currency, direction, target)
        elif not hit:
            self.last_alert_key = None

    def _monitor_loop(self) -> None:
        while self.running:
            try:
                coin_name = self.coin_var.get()
                coin_id = self.coins[coin_name]
                currency = self.currency_var.get().lower()
                target = float(self.target_var.get())
                interval = int(self.interval_var.get())

                price = self.get_price(coin_id, currency)
                self.last_price = price
                self.root.after(0, self._update_live_view, coin_name, coin_id, price, currency, target, interval)

            except RuntimeError as exc:
                self.root.after(0, self._handle_rate_limit_status, str(exc))
            except Exception as exc:
                self.root.after(0, self._set_status, f"Status: Error while monitoring: {exc}")

            waited = 0
            try:
                total_wait = max(5, int(self.interval_var.get()))
            except ValueError:
                total_wait = 60

            while self.running and waited < total_wait:
                if self._is_rate_limited():
                    retry_wait = max(1, min(total_wait - waited, self._seconds_until_retry()))
                    time.sleep(retry_wait)
                    waited += retry_wait
                else:
                    time.sleep(1)
                    waited += 1

    def _update_live_view(self, coin_name: str, coin_id: str, price: float, currency: str, target: float, interval: int) -> None:
        self.current_price_var.set(f"Current price: {price:.8f} {currency.upper()}")
        self.strategy_var.set(self.get_strategy_text(coin_name, currency, price, target))
        self.status_var.set(f"Status: Watching {coin_name} every {interval}s")
        self._check_alert_condition(coin_name, coin_id, currency, price, target)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _handle_rate_limit_status(self, text: str) -> None:
        self.status_var.set(f"Status: {text}")
        self.strategy_var.set(
            "Strategy view: Too many API requests recently. Using cached data where possible and waiting before retrying."
        )

    def _show_alert(self, coin_name: str, price: float, currency: str, direction: str, target: float) -> None:
        self.status_var.set(f"Status: ALERT triggered for {coin_name}")

        if not self.alarm_running:
            threading.Thread(target=self.play_alarm, daemon=True).start()

        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(1500, lambda: self.root.attributes("-topmost", False))

        messagebox.showinfo(
            "Price Alert Triggered",
            f"{coin_name} is now {price:.8f} {currency.upper()}\n\n"
            f"Alert condition: price {direction} {target}\n\n"
            f"{self.get_strategy_text(coin_name, currency, price, target)}",
        )

    def on_close(self) -> None:
        self.running = False
        self.alarm_running = False
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PriceAlertApp(root)
    root.mainloop()
