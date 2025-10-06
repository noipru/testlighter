# Lighter Trading Bots

บอทเทรดอัตโนมัติสำหรับ Lighter.xyz DEX (zk-Rollup Perpetual Trading Platform)

## 📁 ไฟล์ทั้งหมด

| ไฟล์ | คำอธิบาย |
|------|----------|
| `.env` | ไฟล์ Config สำหรับเก็บ API Key และการตั้งค่าบอท |
| `main.py` | **Grid Trading Bot** - วาง orders แบบ Grid (LONG/NEUTRAL/SHORT) พร้อม Auto-Refill |
| `market_maker.py` | **Market Maker Bot** - สร้าง Volume แบบ HFT (วาง BUY+SELL พร้อมกัน) |
| `get_account_info.py` | สคริปช่วยหา ACCOUNT_INDEX ของคุณ |

---

## 🚀 วิธีติดตั้ง

### 1. ติดตั้ง Dependencies
```bash
pip3 install lighter-python python-dotenv requests
```

### 2. ตั้งค่า .env File
แก้ไขไฟล์ `.env` ให้ถูกต้อง:

```bash
# Lighter API Credentials (ห้ามแชร์!)
API_KEY_PRIVATE_KEY=0xYOUR_API_KEY_HERE
ACCOUNT_INDEX=206799
API_KEY_INDEX=0
BASE_URL=https://mainnet.zklighter.elliot.ai

# Grid Bot Configuration
MARKET_INDEX=1              # 0=ETH, 1=BTC, 2=SOL, 3=DOGE, etc.
DIRECTION=NEUTRAL           # LONG / NEUTRAL / SHORT
LEVERAGE=5                  # Leverage 1-25x
GRID_COUNT=30               # จำนวน Grid levels
INVESTMENT_USDC=100         # จำนวนเงินลงทุน (USDC)

# Market Maker Bot (Volume Generator)
SPREAD_PERCENT=0.02         # Spread % (0.02 = 0.02%)
ORDER_SIZE_USDC=30          # ขนาด Order ต่อครั้ง
```

### 3. หา ACCOUNT_INDEX (ถ้ายังไม่มี)
```bash
python3 get_account_info.py
```

---

## 📊 วิธีรันบอท

### 🟢 Grid Trading Bot (main.py)
บอทวาง Grid orders อัตโนมัติ และ Auto-Refill เมื่อ Order ถูก Fill

```bash
python3 main.py
```

**คุณสมบัติ:**
- ✅ วาง Grid orders อัตโนมัติ (30 levels)
- ✅ รองรับ 3 Strategies: LONG (เน้นซื้อ), NEUTRAL (สมดุล), SHORT (เน้นขาย)
- ✅ เปิด Initial Position อัตโนมัติ (Binance-style)
- ✅ Auto-Refill: เติม orders ทันทีที่ถูก Fill
- ✅ HFT Mode: เช็คทุก 2 วินาที

**ตัวอย่าง Output:**
```
============================================================
🤖 Lighter Grid Trading Bot
============================================================
Market: BTC
Direction: NEUTRAL
Leverage: 5x
Grid Count: 30
Investment: $100 USDC

✅ Connected to Lighter
   Account: 206799

📊 Current Price: $121,830.25
   Lower: $121,586.13 (-0.2%)
   Upper: $122,074.37 (+0.2%)
   Grid Spacing: $16.27

✅ Initial position opened: LONG 0.00041 BTC @ $121,830.25

📈 Placing 30 grid orders...
   ✅ Order 1/30 @ $121,586.13 (BUY)
   ✅ Order 2/30 @ $121,602.40 (BUY)
   ...

🔄 Auto-Refill Monitor Started
   Checking every 2 seconds...
```

**หยุดบอท:** กด `Ctrl+C`

---

### 💱 Market Maker Bot (market_maker.py)
บอทสร้าง Volume แบบรวดเร็ว (วาง BUY + SELL พร้อมกัน)

```bash
python3 market_maker.py
```

**คุณสมบัติ:**
- ✅ วาง BUY + SELL orders พร้อมกัน
- ✅ Spread ตั้งค่าได้ (แนะนำ 0.02%)
- ✅ Ultra HFT: เช็คทุก 1 วินาที
- ✅ คำนวณ Profit/Volume อัตโนมัติ

**ตัวอย่าง Output:**
```
============================================================
💱 Lighter Market Making Bot (Volume Generator)
============================================================
Market: BTC
Spread: 0.02%
Order Size: $30 x 5x leverage

✅ Connected to Lighter
   Account: 206799

🔄 Market Making Started
   Monitoring every 1 second (Ultra HFT)

💱 Market Price: $121,830.25
   Spread: 0.02% ($24.37)
   BUY  @ $121,805.88
   SELL @ $121,854.62
   ✅ BUY order placed
   ✅ SELL order placed

   💰 Both filled! Profit: $0.48 | Total Vol: $120 | Trades: 4
```

**หยุดบอท:** กด `Ctrl+C`

---

## ⚙️ การตั้งค่า

### Markets ที่รองรับ
```bash
MARKET_INDEX=0   # ETH
MARKET_INDEX=1   # BTC
MARKET_INDEX=2   # SOL
MARKET_INDEX=3   # DOGE
MARKET_INDEX=4   # 1000PEPE
MARKET_INDEX=5   # WIF
MARKET_INDEX=6   # WLD
MARKET_INDEX=7   # XRP
MARKET_INDEX=8   # LINK
MARKET_INDEX=9   # AVAX
```

### Grid Directions
- **`LONG`** - เน้นซื้อ (คาดว่าราคาจะขึ้น)
  - เปิด Long position ตั้งแต่เริ่ม
  - วาง buy orders เยอะกว่า sell orders
  - Range: -0.5% to +0.2%

- **`NEUTRAL`** - สมดุล (sideways)
  - ไม่เปิด position ตั้งแต่เริ่ม (เริ่ม 50%)
  - วาง orders 2 ฝั่งเท่ากัน
  - Range: -0.2% to +0.2%
  - **เหมาะกับการสร้าง Volume**

- **`SHORT`** - เน้นขาย (คาดว่าราคาจะลง)
  - เปิด Short position ตั้งแต่เริ่ม
  - วาง sell orders เยอะกว่า buy orders
  - Range: -0.2% to +0.5%

---

## 🔧 Troubleshooting

### ❌ Error: "private key does not match"
**แก้:** เช็คให้แน่ใจว่า `API_KEY_INDEX` ใน .env ตรงกับ API Key ที่สร้างจาก Lighter

### ❌ Error: "order price flagged as an accidental price"
**แก้:** ราคา order ห่างจากราคาตลาดเกินไป ลองลด `GRID_COUNT` หรือ ปรับ Range ให้แคบลง

### ❌ Error: "rate limit exceeded"
**แก้:** Lighter จำกัด 60 requests ต่อ 60 วินาที - ลด `GRID_COUNT` หรือ เพิ่ม delay

### ❌ Order ไม่เห็นใน UI
**แก้:** รอ 1-2 วินาที แล้วรีเฟรช หรือเช็คที่ "Open Orders" tab

---

## 🛡️ ความปลอดภัย

⚠️ **คำเตือน:**
- ไฟล์ `.env` มี API Key ของคุณ **ห้ามแชร์ให้ใครเด็ดขาด**
- ไม่แนะนำให้ push ไฟล์ `.env` ขึ้น GitHub
- ควรเริ่มทดลองด้วยเงินน้อย ๆ ก่อน

---

## 📝 หมายเหตุ

- บอททั้งหมดใช้ **POST_ONLY** orders (ไม่กิน liquidity)
- Auto-Refill จะเติม orders ทันทีที่ถูก Fill
- Rate limit: **60 requests ต่อ 60 วินาที**
- ควรตั้ง `GRID_COUNT` ไม่เกิน 30-40 เพื่อไม่ติด rate limit

---

## 💡 Tips

1. **NEUTRAL Mode** เหมาะกับการสร้าง Volume แบบไม่เสี่ยง
2. **Market Maker** ใช้สำหรับ HFT และสร้าง Volume สูง
3. ตั้ง `SPREAD_PERCENT` ต่ำ (0.01-0.05%) จะได้ Volume เยอะ
4. ใช้ `LEVERAGE` สูง (10-25x) จะได้ Volume มากขึ้น
5. เช็ค Balance บ่อย ๆ ด้วยคำสั่ง: `python3 get_account_info.py`

---

## 🤝 Support

ถ้ามีปัญหาหรือต้องการความช่วยเหลือ:
- Lighter Docs: https://docs.lighter.xyz
- Lighter Discord: https://discord.gg/lighter

---

**Happy Trading! 🚀**
