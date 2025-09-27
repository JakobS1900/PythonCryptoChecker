"""
Universal cryptocurrency converter.
Handles conversions between crypto pairs and fiat currencies.
"""

import asyncio
import aiohttp
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from .price_service import price_service

class CryptoConverter:
    """Universal cryptocurrency and fiat currency converter."""

    def __init__(self):
        self.fiat_cache: Dict[str, float] = {}
        self.fiat_cache_expiry: Dict[str, datetime] = {}
        self.fiat_cache_duration = 300  # 5 minutes for fiat rates
        self.symbol_to_id_cache: Dict[str, str] = {}

        # Supported fiat currencies
        self.supported_fiat = {
            "USD": "US Dollar",
            "EUR": "Euro",
            "GBP": "British Pound",
            "JPY": "Japanese Yen",
            "CNY": "Chinese Yuan",
            "KRW": "South Korean Won",
            "AUD": "Australian Dollar",
            "CAD": "Canadian Dollar",
            "CHF": "Swiss Franc",
            "SEK": "Swedish Krona",
            "NOK": "Norwegian Krone",
            "DKK": "Danish Krone",
            "PLN": "Polish Zloty",
            "CZK": "Czech Koruna",
            "HUF": "Hungarian Forint",
            "RUB": "Russian Ruble",
            "BRL": "Brazilian Real",
            "INR": "Indian Rupee",
            "SGD": "Singapore Dollar",
            "HKD": "Hong Kong Dollar",
            "MXN": "Mexican Peso",
            "TRY": "Turkish Lira",
            "ZAR": "South African Rand",
            "AED": "UAE Dirham",
            "SAR": "Saudi Riyal"
        }

    async def resolve_crypto_symbol_to_id(self, symbol: str) -> Optional[str]:
        """Resolve a cryptocurrency symbol to its ID."""
        try:
            symbol = symbol.upper()

            # Check cache first
            if symbol in self.symbol_to_id_cache:
                return self.symbol_to_id_cache[symbol]

            # Get all cryptocurrencies to build symbol-to-ID mapping
            cryptos = await price_service.get_all_cryptos()

            # Build and cache the mapping
            for crypto in cryptos:
                crypto_symbol = crypto.get("symbol", "").upper()
                crypto_id = crypto.get("id", "")
                if crypto_symbol and crypto_id:
                    self.symbol_to_id_cache[crypto_symbol] = crypto_id

            # Return the requested mapping
            return self.symbol_to_id_cache.get(symbol)

        except Exception as e:
            print(f">> Error: Error resolving symbol {symbol}: {e}")
            return None

    async def convert_crypto_to_crypto(
        self,
        from_crypto: str,
        to_crypto: str,
        amount: float
    ) -> Optional[float]:
        """Convert between two cryptocurrencies."""
        try:
            # Resolve symbols to IDs
            from_id = await self.resolve_crypto_symbol_to_id(from_crypto)
            to_id = await self.resolve_crypto_symbol_to_id(to_crypto)

            if from_id is None or to_id is None:
                print(f">> Error: Could not resolve symbols {from_crypto} or {to_crypto} to IDs")
                return None

            # Get prices for both cryptocurrencies
            from_price = await price_service.get_price(from_id)
            to_price = await price_service.get_price(to_id)

            if from_price is None or to_price is None:
                print(f">> Error: Could not get prices for {from_id} or {to_id}")
                return None

            # Convert via USD
            usd_value = amount * from_price
            converted_amount = usd_value / to_price

            return converted_amount

        except Exception as e:
            print(f">> Error: Error converting {from_crypto} to {to_crypto}: {e}")
            return None

    async def convert_crypto_to_fiat(
        self,
        crypto: str,
        fiat: str,
        amount: float
    ) -> Optional[float]:
        """Convert cryptocurrency to fiat currency."""
        try:
            # Resolve symbol to ID
            crypto_id = await self.resolve_crypto_symbol_to_id(crypto)
            if crypto_id is None:
                print(f">> Error: Could not resolve symbol {crypto} to ID")
                return None

            # Get crypto price in USD
            crypto_price_usd = await price_service.get_price(crypto_id)
            if crypto_price_usd is None:
                print(f">> Error: Could not get price for {crypto_id}")
                return None

            # Calculate USD value
            usd_value = amount * crypto_price_usd

            # If target is USD, return directly
            if fiat.upper() == "USD":
                return usd_value

            # Get fiat exchange rate
            fiat_rate = await self._get_fiat_rate(fiat.upper())
            if fiat_rate is None:
                return None

            # Convert to target fiat
            return usd_value * fiat_rate

        except Exception as e:
            print(f">> Error: Error converting {crypto} to {fiat}: {e}")
            return None

    async def convert_fiat_to_crypto(
        self,
        fiat: str,
        crypto: str,
        amount: float
    ) -> Optional[float]:
        """Convert fiat currency to cryptocurrency."""
        try:
            # Convert fiat to USD first
            if fiat.upper() == "USD":
                usd_value = amount
            else:
                fiat_rate = await self._get_fiat_rate(fiat.upper())
                if fiat_rate is None:
                    return None
                usd_value = amount / fiat_rate

            # Resolve symbol to ID
            crypto_id = await self.resolve_crypto_symbol_to_id(crypto)
            if crypto_id is None:
                print(f">> Error: Could not resolve symbol {crypto} to ID")
                return None

            # Get crypto price in USD
            crypto_price_usd = await price_service.get_price(crypto_id)
            if crypto_price_usd is None:
                print(f">> Error: Could not get price for {crypto_id}")
                return None

            # Convert USD to crypto
            return usd_value / crypto_price_usd

        except Exception as e:
            print(f">> Error: Error converting {fiat} to {crypto}: {e}")
            return None

    async def convert_fiat_to_fiat(
        self,
        from_fiat: str,
        to_fiat: str,
        amount: float
    ) -> Optional[float]:
        """Convert between two fiat currencies."""
        try:
            from_fiat = from_fiat.upper()
            to_fiat = to_fiat.upper()

            if from_fiat == to_fiat:
                return amount

            # Convert via USD
            if from_fiat == "USD":
                usd_value = amount
            else:
                from_rate = await self._get_fiat_rate(from_fiat)
                if from_rate is None:
                    return None
                usd_value = amount / from_rate

            if to_fiat == "USD":
                return usd_value

            to_rate = await self._get_fiat_rate(to_fiat)
            if to_rate is None:
                return None

            return usd_value * to_rate

        except Exception as e:
            print(f">> Error: Error converting {from_fiat} to {to_fiat}: {e}")
            return None

    async def universal_convert(
        self,
        from_currency: str,
        to_currency: str,
        amount: float
    ) -> Optional[Dict]:
        """Universal converter that auto-detects currency types."""
        try:
            from_currency = from_currency.upper()
            to_currency = to_currency.upper()

            from_is_fiat = from_currency in self.supported_fiat
            to_is_fiat = to_currency in self.supported_fiat

            result = None

            if not from_is_fiat and not to_is_fiat:
                # Crypto to crypto
                result = await self.convert_crypto_to_crypto(from_currency, to_currency, amount)
                conversion_type = "crypto_to_crypto"
            elif not from_is_fiat and to_is_fiat:
                # Crypto to fiat
                result = await self.convert_crypto_to_fiat(from_currency, to_currency, amount)
                conversion_type = "crypto_to_fiat"
            elif from_is_fiat and not to_is_fiat:
                # Fiat to crypto
                result = await self.convert_fiat_to_crypto(from_currency, to_currency, amount)
                conversion_type = "fiat_to_crypto"
            else:
                # Fiat to fiat
                result = await self.convert_fiat_to_fiat(from_currency, to_currency, amount)
                conversion_type = "fiat_to_fiat"

            if result is not None:
                return {
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "from_amount": amount,
                    "to_amount": result,
                    "conversion_type": conversion_type,
                    "rate": result / amount if amount > 0 else 0,
                    "timestamp": datetime.utcnow().isoformat()
                }

            return None

        except Exception as e:
            print(f">> Error: Error in universal conversion: {e}")
            return None

    async def _get_fiat_rate(self, fiat_code: str) -> Optional[float]:
        """Get fiat currency exchange rate to USD."""
        try:
            # Check cache first
            if fiat_code in self.fiat_cache and fiat_code in self.fiat_cache_expiry:
                if datetime.utcnow() < self.fiat_cache_expiry[fiat_code]:
                    return self.fiat_cache[fiat_code]

            # Fetch from exchange rate API
            async with aiohttp.ClientSession() as session:
                # Using exchangerate-api.com (free tier: 1500 requests/month)
                url = f"https://api.exchangerate-api.com/v4/latest/USD"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        rates = data.get("rates", {})

                        if fiat_code in rates:
                            rate = rates[fiat_code]

                            # Cache the rate
                            self.fiat_cache[fiat_code] = rate
                            self.fiat_cache_expiry[fiat_code] = datetime.utcnow() + timedelta(seconds=self.fiat_cache_duration)

                            return rate

            return None

        except Exception as e:
            print(f">> Error: Error fetching fiat rate for {fiat_code}: {e}")
            return None

    def get_supported_fiat_currencies(self) -> Dict[str, str]:
        """Get list of supported fiat currencies."""
        return self.supported_fiat.copy()

    async def get_supported_crypto_currencies(self) -> Dict[str, str]:
        """Get list of supported cryptocurrencies."""
        cryptos = await price_service.get_all_cryptos()
        return {crypto["symbol"].upper(): crypto["name"] for crypto in cryptos}

    async def get_popular_pairs(self) -> Dict[str, list]:
        """Get popular conversion pairs."""
        return {
            "crypto_to_fiat": [
                {"from": "BTC", "to": "USD"},
                {"from": "ETH", "to": "USD"},
                {"from": "BTC", "to": "EUR"},
                {"from": "ETH", "to": "EUR"},
                {"from": "BTC", "to": "JPY"},
                {"from": "DOGE", "to": "USD"}
            ],
            "crypto_to_crypto": [
                {"from": "BTC", "to": "ETH"},
                {"from": "ETH", "to": "BTC"},
                {"from": "BTC", "to": "ADA"},
                {"from": "ETH", "to": "SOL"},
                {"from": "BNB", "to": "BTC"},
                {"from": "XRP", "to": "ETH"}
            ],
            "fiat_to_crypto": [
                {"from": "USD", "to": "BTC"},
                {"from": "EUR", "to": "BTC"},
                {"from": "JPY", "to": "BTC"},
                {"from": "USD", "to": "ETH"},
                {"from": "GBP", "to": "BTC"},
                {"from": "CAD", "to": "ETH"}
            ],
            "fiat_to_fiat": [
                {"from": "USD", "to": "EUR"},
                {"from": "EUR", "to": "USD"},
                {"from": "GBP", "to": "USD"},
                {"from": "JPY", "to": "USD"},
                {"from": "CAD", "to": "USD"},
                {"from": "AUD", "to": "USD"}
            ]
        }

# Global converter instance
crypto_converter = CryptoConverter()