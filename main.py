"""
Lighter Grid Trading Bot (AUTO)
Supports: Long, Neutral, Short strategies (Binance-style)
Features: Auto-refill, Profit tracking, Real-time monitoring
"""
import asyncio
import os
import signal
from datetime import datetime
from dotenv import load_dotenv
import lighter
import requests

load_dotenv()

class GridTradingBot:
    # Market symbols สำหรับแสดงผล
    MARKETS = {
        0: "ETH", 1: "BTC", 2: "SOL", 3: "DOGE", 4: "1000PEPE",
        5: "WIF", 6: "WLD", 7: "XRP", 8: "LINK", 9: "AVAX"
    }

    def __init__(self):
        self.api_key_pk = os.getenv('API_KEY_PRIVATE_KEY')
        self.account_index = int(os.getenv('ACCOUNT_INDEX'))
        self.api_key_index = int(os.getenv('API_KEY_INDEX'))
        self.base_url = os.getenv('BASE_URL')
        self.market_index = int(os.getenv('MARKET_INDEX', 1))
        self.leverage = int(os.getenv('LEVERAGE', 10))
        self.grid_count = int(os.getenv('GRID_COUNT', 20))
        self.investment = float(os.getenv('INVESTMENT_USDC', 100))
        self.direction = os.getenv('DIRECTION', 'LONG').upper()  # LONG, NEUTRAL, SHORT
        self.client = None
        self.order_index = 30000
        self.market_symbol = self.MARKETS.get(self.market_index, f"Market{self.market_index}")

        # Auto-refill tracking
        self.running = True
        self.grid_orders = {}  # {price: {'client_order_index': int, 'is_ask': bool, 'base_amount': int}}
        self.filled_orders = []
        self.total_profit = 0.0
        self.trades_count = 0
        self.total_volume = 0.0  # Track total trading volume

    async def init(self):
        self.client = lighter.SignerClient(
            url=self.base_url,
            private_key=self.api_key_pk,
            account_index=self.account_index,
            api_key_index=self.api_key_index
        )

        err = self.client.check_client()
        if err:
            raise Exception(f"Client error: {err}")

        print(f"✅ Connected to Lighter")
        print(f"   Account: {self.account_index}")

    async def get_current_price(self):
        """Get current price from order book"""
        url = f"{self.base_url}/api/v1/orderBookOrders?market_id={self.market_index}&limit=1"
        response = requests.get(url)
        data = response.json()

        best_bid = data['bids'][0]['price']
        best_ask = data['asks'][0]['price']
        current_price = (float(best_bid) + float(best_ask)) / 2

        return current_price, best_bid, best_ask

    async def calculate_grid_levels(self):
        """Calculate grid price levels based on direction"""
        current_price, best_bid, best_ask = await self.get_current_price()

        # Lighter มี price validation เข้มงวด - ใช้ ±0.5% only
        if self.direction == 'LONG':
            # Long: วาง buy orders เยอะกว่า (bias ลง)
            self.lower_price = current_price * 0.995  # -0.5%
            self.upper_price = current_price * 1.002  # +0.2%
        elif self.direction == 'SHORT':
            # Short: วาง sell orders เยอะกว่า (bias ขึ้น)
            self.lower_price = current_price * 0.998  # -0.2%
            self.upper_price = current_price * 1.005  # +0.5%
        else:  # NEUTRAL - HIGH FREQUENCY (เน้น Volume)
            # Neutral: แคบมาก ๆ ±0.2% เพื่อให้เทรดบ่อย
            self.lower_price = current_price * 0.998  # -0.2%
            self.upper_price = current_price * 1.002  # +0.2%

        spacing = (self.upper_price - self.lower_price) / (self.grid_count - 1)
        grid_levels = [self.lower_price + (i * spacing) for i in range(self.grid_count)]

        print(f"\n📊 Grid Setup ({self.direction}):")
        print(f"   {self.market_symbol} Price: ${current_price:,.2f}")
        print(f"   Best Bid: ${best_bid}")
        print(f"   Best Ask: ${best_ask}")
        print(f"   Range: ${self.lower_price:,.2f} - ${self.upper_price:,.2f}")
        print(f"   Grids: {self.grid_count}")
        print(f"   Spacing: ${spacing:.4f}")
        print(f"   💡 Mode: {'HIGH FREQUENCY (Volume focus)' if self.direction == 'NEUTRAL' else 'Standard'}")

        return grid_levels, current_price

    def price_to_int(self, price_float):
        """แปลง price เป็น int (ลบจุดทศนิยม)"""
        price_str = f"{price_float:.1f}"
        price_int = int(price_str.replace(".", ""))
        return price_int

    async def place_initial_position(self, current_price):
        """
        เปิด initial position ตาม direction (Binance-style)
        - LONG: ซื้อที่ราคาตลาด (50% ของ investment)
        - NEUTRAL: ซื้อ 50% ก่อน เพื่อมี position เริ่มต้น
        - SHORT: ขายที่ราคาตลาด (50% ของ investment)
        """
        # NEUTRAL mode: เข้า 50% ก่อน (Binance Grid style)
        if self.direction == 'NEUTRAL':
            initial_percent = 0.5  # ใช้ 50% ของ investment
        else:
            initial_percent = 1.0  # LONG/SHORT ใช้เต็ม

        # คำนวณขนาด position
        coin_amount = (self.investment * self.leverage * initial_percent) / current_price
        base_amount = int(coin_amount * 1e8)

        # NEUTRAL และ LONG = BUY, SHORT = SELL
        is_ask = (self.direction == 'SHORT')

        if self.direction == 'NEUTRAL':
            action = "NEUTRAL Entry (Buy 50%)"
        else:
            action = "SHORT (Sell)" if is_ask else "LONG (Buy)"

        price_int = self.price_to_int(current_price * (0.999 if is_ask else 1.001))

        print(f"\n🚀 Opening {action} Position:")
        print(f"   Amount: {coin_amount:.8f} {self.market_symbol}")
        print(f"   Value: ${self.investment * self.leverage * initial_percent:.2f}")
        print(f"   Price: ${current_price:,.2f}")

        try:
            tx, tx_hash, err = await self.client.create_order(
                market_index=self.market_index,
                client_order_index=self.order_index,
                base_amount=base_amount,
                price=price_int,
                is_ask=is_ask,
                order_type=lighter.SignerClient.ORDER_TYPE_LIMIT,
                time_in_force=lighter.SignerClient.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
                reduce_only=False,
                trigger_price=0
            )

            self.order_index += 1

            if err:
                print(f"   ⚠️  {err}")
                return False
            else:
                print(f"   ✅ Position opened!")
                await asyncio.sleep(2)  # รอให้ order execute
                return True

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    async def place_grid_orders(self, grid_levels, current_price):
        """วาง grid limit orders และบันทึกใน grid_orders"""
        coin_per_order = (self.investment / self.grid_count * self.leverage) / current_price
        base_amount = int(coin_per_order * 1e8)

        orders_placed = {'buy': 0, 'sell': 0}

        print(f"\n📝 Placing Grid Orders:")
        print(f"   Amount per order: {coin_per_order:.8f} {self.market_symbol}")
        print(f"   Base amount: {base_amount}\n")

        for i, price in enumerate(grid_levels, 1):
            # วาง orders ทุกระดับ ไม่ skip (เพื่อ Balance เต็มที่)
            is_ask = price > current_price
            price_int = self.price_to_int(price)

            try:
                tx, tx_hash, err = await self.client.create_order(
                    market_index=self.market_index,
                    client_order_index=self.order_index,
                    base_amount=base_amount,
                    price=price_int,
                    is_ask=is_ask,
                    order_type=lighter.SignerClient.ORDER_TYPE_LIMIT,
                    time_in_force=lighter.SignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,
                    reduce_only=False,
                    trigger_price=0
                )

                if not err:
                    # บันทึก order ใน grid_orders เพื่อ monitor
                    self.grid_orders[price] = {
                        'client_order_index': self.order_index,
                        'is_ask': is_ask,
                        'base_amount': base_amount,
                        'price_int': price_int
                    }
                    orders_placed['sell' if is_ask else 'buy'] += 1
                    if i % 5 == 0 or i <= 3:
                        print(f"   ✓ {'SELL' if is_ask else 'BUY'} @ ${price:,.2f}")
                else:
                    if i <= 3:
                        print(f"   ✗ {'SELL' if is_ask else 'BUY'} @ ${price:,.2f} - {str(err)[:50]}")

                self.order_index += 1
                await asyncio.sleep(0.8)  # เร็วขึ้น สำหรับ HFT

            except Exception as e:
                if i <= 3:
                    print(f"   ✗ Error at ${price:,.2f}: {str(e)[:50]}")

        print(f"\n✅ Grid Complete:")
        print(f"   {orders_placed['buy']} buy orders")
        print(f"   {orders_placed['sell']} sell orders")

        return orders_placed

    async def get_active_orders(self):
        """ดู orders ที่ active ผ่าน REST API"""
        try:
            # Create auth token
            auth_token, err = self.client.create_auth_token_with_expiry()
            if err:
                print(f"   ⚠️  Auth error: {err}")
                return []

            # Call API
            url = f"{self.base_url}/api/v1/accountActiveOrders?account_index={self.account_index}&market_id={self.market_index}"
            headers = {"Authorization": auth_token}
            response = requests.get(url, headers=headers)
            data = response.json()

            if 'orders' in data:
                return data['orders']
            return []

        except Exception as e:
            print(f"   ⚠️  Error getting orders: {e}")
            return []

    async def monitor_and_refill(self):
        """Monitor orders และ auto-refill เมื่อถูก fill (HFT Mode)"""
        print(f"\n🔄 Auto-Refill Mode Started (HFT)")
        print(f"   Monitoring every 2 seconds")
        print(f"   Press Ctrl+C to stop\n")

        check_interval = 2  # HFT mode: เช็คทุก 2 วินาที!

        while self.running:
            try:
                # ดู active orders
                active_orders = await self.get_active_orders()
                active_prices = set()

                for order in active_orders:
                    price_str = order.get('price', '0')
                    # แปลง price กลับเป็น float
                    price_float = float(price_str) / (10 ** len(price_str.split('.')[0]))
                    active_prices.add(round(price_float, 1))

                # เช็คว่า grid order ไหนถูก fill (หายไปจาก active orders)
                filled_prices = []
                for grid_price in list(self.grid_orders.keys()):
                    if grid_price not in active_prices:
                        filled_prices.append(grid_price)

                # Refill orders ที่ถูก fill
                for price in filled_prices:
                    order_info = self.grid_orders[price]
                    was_ask = order_info['is_ask']

                    # Calculate volume
                    coin_amount = order_info['base_amount'] / 1e8
                    volume_usd = coin_amount * price
                    self.total_volume += volume_usd
                    self.trades_count += 1

                    # คำนวณ profit (ถ้า SELL ถูก fill แล้ว, ต่อไปจะ BUY ในราคาต่ำกว่า)
                    if was_ask:
                        # SELL order filled -> วาง BUY order ที่ราคาเดิม
                        profit = (price - self.lower_price) * 0.001  # ประมาณการ
                        self.total_profit += profit
                        print(f"   💰 SELL @ ${price:,.2f} | Volume: ${volume_usd:.0f} | Total Vol: ${self.total_volume:.0f}")

                        # วาง BUY order ใหม่ที่ราคาเดิม
                        await self.refill_order(price, False, order_info['base_amount'])
                    else:
                        # BUY order filled -> วาง SELL order ที่ราคาเดิม
                        print(f"   📈 BUY @ ${price:,.2f} | Volume: ${volume_usd:.0f} | Total Vol: ${self.total_volume:.0f}")

                        # วาง SELL order ใหม่ที่ราคาเดิม
                        await self.refill_order(price, True, order_info['base_amount'])

                    # ลบ order เก่าออก
                    del self.grid_orders[price]

                # รอก่อนเช็คอีกรอบ
                await asyncio.sleep(check_interval)

            except Exception as e:
                print(f"   ⚠️  Monitor error: {e}")
                await asyncio.sleep(check_interval)

    async def refill_order(self, price, is_ask, base_amount):
        """วาง order ใหม่แทนที่ถูก fill"""
        try:
            price_int = self.price_to_int(price)

            tx, tx_hash, err = await self.client.create_order(
                market_index=self.market_index,
                client_order_index=self.order_index,
                base_amount=base_amount,
                price=price_int,
                is_ask=is_ask,
                order_type=lighter.SignerClient.ORDER_TYPE_LIMIT,
                time_in_force=lighter.SignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,
                reduce_only=False,
                trigger_price=0
            )

            if not err:
                # บันทึก order ใหม่
                self.grid_orders[price] = {
                    'client_order_index': self.order_index,
                    'is_ask': is_ask,
                    'base_amount': base_amount,
                    'price_int': price_int
                }
                print(f"   ✅ Refilled {'SELL' if is_ask else 'BUY'} @ ${price:,.2f}")
            else:
                print(f"   ⚠️  Refill failed @ ${price:,.2f}: {err}")

            self.order_index += 1

        except Exception as e:
            print(f"   ❌ Refill error: {e}")

    def stop_bot(self, signum=None, frame=None):
        """Stop bot gracefully"""
        print(f"\n\n⏹️  Stopping bot...")
        print(f"📊 Final Stats:")
        print(f"   Total Trades: {self.trades_count}")
        print(f"   Total Volume: ${self.total_volume:.2f}")
        print(f"   Total Profit: ${self.total_profit:.2f}")
        self.running = False

    async def run(self):
        """Main bot execution with auto-refill"""
        # Setup signal handler for Ctrl+C
        signal.signal(signal.SIGINT, self.stop_bot)

        try:
            print("=" * 60)
            print(f"🤖 Lighter Auto Grid Trading Bot")
            print("=" * 60)
            print(f"Market: {self.market_symbol} | Direction: {self.direction}")
            print(f"Leverage: {self.leverage}x | Grids: {self.grid_count}")

            await self.init()

            grid_levels, current_price = await self.calculate_grid_levels()

            # เปิด initial position (Binance-style)
            await self.place_initial_position(current_price)

            # วาง grid orders
            await self.place_grid_orders(grid_levels, current_price)

            print(f"\n{'='*60}")
            print("✅ Grid Bot Setup Complete!")
            print(f"🔍 ดู orders ที่: https://app.lighter.xyz")
            print("=" * 60)

            # เริ่ม auto-monitor และ refill
            await self.monitor_and_refill()

        except KeyboardInterrupt:
            self.stop_bot()
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.client:
                await self.client.close()
            print("\n👋 Bot stopped successfully")

if __name__ == "__main__":
    bot = GridTradingBot()
    asyncio.run(bot.run())
