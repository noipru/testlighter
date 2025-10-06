"""
Lighter Market Making Bot (Volume Generator)
Strategy: Place BUY + SELL orders simultaneously with small spread
High-frequency trading for maximum volume
"""
import asyncio
import os
import signal
from datetime import datetime
from dotenv import load_dotenv
import lighter
import requests

load_dotenv()

class MarketMakerBot:
    # Market symbols
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
        self.leverage = int(os.getenv('LEVERAGE', 5))
        self.spread_percent = float(os.getenv('SPREAD_PERCENT', 0.05))  # 0.05% spread
        self.order_size_usd = float(os.getenv('ORDER_SIZE_USDC', 20))  # $20 per order

        self.client = None
        self.order_index = 40000
        self.market_symbol = self.MARKETS.get(self.market_index, f"Market{self.market_index}")

        # Tracking
        self.running = True
        self.total_volume = 0.0
        self.trades_count = 0
        self.profit = 0.0
        self.active_buy_price = None
        self.active_sell_price = None

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
        """Get current market price"""
        url = f"{self.base_url}/api/v1/orderBookOrders?market_id={self.market_index}&limit=1"
        response = requests.get(url)
        data = response.json()

        best_bid = float(data['bids'][0]['price'])
        best_ask = float(data['asks'][0]['price'])
        mid_price = (best_bid + best_ask) / 2

        return mid_price

    def price_to_int(self, price_float):
        """Convert price to int format"""
        price_str = f"{price_float:.1f}"
        price_int = int(price_str.replace(".", ""))
        return price_int

    async def place_market_making_orders(self):
        """Place BUY + SELL orders simultaneously with spread"""
        try:
            # Get current price
            current_price = await self.get_current_price()

            # Calculate spread prices
            spread_amount = current_price * (self.spread_percent / 100)
            buy_price = current_price - spread_amount
            sell_price = current_price + spread_amount

            # Calculate order size
            coin_amount = (self.order_size_usd * self.leverage) / current_price
            base_amount = int(coin_amount * 1e8)

            print(f"\n💱 Market Price: ${current_price:,.2f}")
            print(f"   Spread: {self.spread_percent}% (${spread_amount:.2f})")
            print(f"   BUY  @ ${buy_price:,.2f}")
            print(f"   SELL @ ${sell_price:,.2f}")

            # Place BUY order
            buy_tx, buy_hash, buy_err = await self.client.create_order(
                market_index=self.market_index,
                client_order_index=self.order_index,
                base_amount=base_amount,
                price=self.price_to_int(buy_price),
                is_ask=False,
                order_type=lighter.SignerClient.ORDER_TYPE_LIMIT,
                time_in_force=lighter.SignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,
                reduce_only=False,
                trigger_price=0
            )

            self.order_index += 1

            if not buy_err:
                self.active_buy_price = buy_price
                print(f"   ✅ BUY order placed @ ${buy_price:,.2f}")
            else:
                print(f"   ❌ BUY failed: {buy_err}")

            await asyncio.sleep(0.3)

            # Place SELL order
            sell_tx, sell_hash, sell_err = await self.client.create_order(
                market_index=self.market_index,
                client_order_index=self.order_index,
                base_amount=base_amount,
                price=self.price_to_int(sell_price),
                is_ask=True,
                order_type=lighter.SignerClient.ORDER_TYPE_LIMIT,
                time_in_force=lighter.SignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,
                reduce_only=False,
                trigger_price=0
            )

            self.order_index += 1

            if not sell_err:
                self.active_sell_price = sell_price
                print(f"   ✅ SELL order placed @ ${sell_price:,.2f}")
            else:
                print(f"   ❌ SELL failed: {sell_err}")

            return buy_price, sell_price

        except Exception as e:
            print(f"   ⚠️  Error placing orders: {e}")
            return None, None

    async def get_active_orders(self):
        """Get active orders"""
        try:
            auth_token, err = self.client.create_auth_token_with_expiry()
            if err:
                return []

            url = f"{self.base_url}/api/v1/accountActiveOrders?account_index={self.account_index}&market_id={self.market_index}"
            headers = {"Authorization": auth_token}
            response = requests.get(url, headers=headers)
            data = response.json()

            if 'orders' in data:
                return data['orders']
            return []

        except Exception as e:
            return []

    async def monitor_and_refill(self):
        """Monitor orders and refill when both sides fill"""
        print(f"\n🔄 Market Making Started")
        print(f"   Monitoring every 1 second (Ultra HFT)")
        print(f"   Press Ctrl+C to stop\n")

        # Place initial orders
        buy_price, sell_price = await self.place_market_making_orders()

        check_interval = 1  # Ultra fast: 1 second

        while self.running:
            try:
                await asyncio.sleep(check_interval)

                # Check if orders are filled
                active_orders = await self.get_active_orders()
                active_count = len(active_orders)

                # If no active orders = both filled!
                if active_count == 0 and self.active_buy_price and self.active_sell_price:
                    # Calculate profit (spread)
                    volume = self.order_size_usd * 2  # Both sides
                    profit = (self.active_sell_price - self.active_buy_price) * (self.order_size_usd / self.active_buy_price)

                    self.total_volume += volume
                    self.trades_count += 2
                    self.profit += profit

                    print(f"   💰 Both filled! Profit: ${profit:.2f} | Total Vol: ${self.total_volume:.0f} | Trades: {self.trades_count}")

                    # Place new orders immediately
                    self.active_buy_price = None
                    self.active_sell_price = None
                    buy_price, sell_price = await self.place_market_making_orders()

                # If only 1 order filled, re-place the pair
                elif active_count == 1 and (self.active_buy_price or self.active_sell_price):
                    filled_side = "BUY" if active_count == 1 and self.active_sell_price else "SELL"
                    volume = self.order_size_usd

                    self.total_volume += volume
                    self.trades_count += 1

                    print(f"   📊 {filled_side} filled | Vol: ${volume:.0f} | Total: ${self.total_volume:.0f}")

                    # Cancel remaining and place new pair
                    self.active_buy_price = None
                    self.active_sell_price = None
                    buy_price, sell_price = await self.place_market_making_orders()

            except Exception as e:
                print(f"   ⚠️  Monitor error: {e}")
                await asyncio.sleep(check_interval)

    def stop_bot(self, signum=None, frame=None):
        """Stop bot gracefully"""
        print(f"\n\n⏹️  Stopping Market Maker...")
        print(f"📊 Final Stats:")
        print(f"   Total Trades: {self.trades_count}")
        print(f"   Total Volume: ${self.total_volume:.2f}")
        print(f"   Total Profit: ${self.profit:.2f}")
        self.running = False

    async def run(self):
        """Main execution"""
        signal.signal(signal.SIGINT, self.stop_bot)

        try:
            print("=" * 60)
            print(f"💱 Lighter Market Making Bot (Volume Generator)")
            print("=" * 60)
            print(f"Market: {self.market_symbol}")
            print(f"Spread: {self.spread_percent}%")
            print(f"Order Size: ${self.order_size_usd} x {self.leverage}x leverage")

            await self.init()

            # Start market making
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
            print("\n👋 Market Maker stopped")

if __name__ == "__main__":
    bot = MarketMakerBot()
    asyncio.run(bot.run())
