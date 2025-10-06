"""
Get Account Information from Lighter.xyz
Shows: Account Index, Balance, Positions
"""
import asyncio
import os
from dotenv import load_dotenv
import lighter

load_dotenv()

async def get_account_info():
    # Load credentials
    api_key_pk = os.getenv('API_KEY_PRIVATE_KEY')
    account_index = int(os.getenv('ACCOUNT_INDEX', 0))
    api_key_index = int(os.getenv('API_KEY_INDEX', 0))
    base_url = os.getenv('BASE_URL')

    print("=" * 60)
    print("🔍 Lighter Account Information")
    print("=" * 60)

    # Connect to Lighter
    client = lighter.SignerClient(
        url=base_url,
        private_key=api_key_pk,
        account_index=account_index,
        api_key_index=api_key_index
    )

    err = client.check_client()
    if err:
        print(f"❌ Connection error: {err}")
        return

    print(f"✅ Connected to Lighter\n")

    # Display account info
    print(f"📋 Account Details:")
    print(f"   ACCOUNT_INDEX: {account_index}")
    print(f"   API_KEY_INDEX: {api_key_index}")
    print(f"   Base URL: {base_url}")

    print("\n" + "=" * 60)
    print("✅ Copy this value to your .env file:")
    print(f"\n   ACCOUNT_INDEX={account_index}")
    print("\n" + "=" * 60)

    await client.close()

if __name__ == "__main__":
    asyncio.run(get_account_info())
