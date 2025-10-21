"""
Simplified Crypto Roulette Engine.
Clean, focused implementation with proper GEM economy integration.
"""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import GameSession, GameBet, GameStatus, BetType, TransactionType
from database.database import AsyncSessionLocal
from crypto.portfolio import portfolio_manager

class CryptoRouletteEngine:
    """Simplified crypto-themed roulette engine with provably fair mechanics."""

    def __init__(self):
        # Crypto wheel configuration (37 positions: 0-36)
        self.crypto_wheel = {
            0: {"crypto": "BTC", "color": "green", "category": "Layer1"},    # Bitcoin is always 0 (green)
            1: {"crypto": "ETH", "color": "red", "category": "Layer1"},     # Ethereum
            2: {"crypto": "BNB", "color": "black", "category": "Exchange"}, # Binance Coin
            3: {"crypto": "ADA", "color": "red", "category": "Layer1"},     # Cardano
            4: {"crypto": "SOL", "color": "black", "category": "Layer1"},   # Solana
            5: {"crypto": "XRP", "color": "red", "category": "Payment"},    # Ripple
            6: {"crypto": "DOT", "color": "black", "category": "Layer0"},   # Polkadot
            7: {"crypto": "DOGE", "color": "red", "category": "Meme"},      # Dogecoin
            8: {"crypto": "AVAX", "color": "black", "category": "Layer1"},  # Avalanche
            9: {"crypto": "SHIB", "color": "red", "category": "Meme"},      # Shiba Inu
            10: {"crypto": "MATIC", "color": "black", "category": "Layer2"}, # Polygon
            11: {"crypto": "UNI", "color": "red", "category": "DeFi"},      # Uniswap
            12: {"crypto": "LINK", "color": "black", "category": "Oracle"}, # Chainlink
            13: {"crypto": "LTC", "color": "red", "category": "Payment"},   # Litecoin
            14: {"crypto": "ATOM", "color": "black", "category": "Layer0"}, # Cosmos
            15: {"crypto": "BCH", "color": "red", "category": "Payment"},   # Bitcoin Cash
            16: {"crypto": "FIL", "color": "black", "category": "Storage"}, # Filecoin
            17: {"crypto": "TRX", "color": "red", "category": "Layer1"},    # TRON
            18: {"crypto": "ETC", "color": "black", "category": "Layer1"},  # Ethereum Classic
            19: {"crypto": "XLM", "color": "red", "category": "Payment"},   # Stellar
            20: {"crypto": "THETA", "color": "black", "category": "Media"}, # Theta
            21: {"crypto": "VET", "color": "red", "category": "Supply"},    # VeChain
            22: {"crypto": "ALGO", "color": "black", "category": "Layer1"}, # Algorand
            23: {"crypto": "ICP", "color": "red", "category": "Layer1"},    # Internet Computer
            24: {"crypto": "HBAR", "color": "black", "category": "Layer1"}, # Hedera
            25: {"crypto": "FLOW", "color": "red", "category": "NFT"},      # Flow
            26: {"crypto": "MANA", "color": "black", "category": "Metaverse"}, # Decentraland
            27: {"crypto": "SAND", "color": "red", "category": "Metaverse"}, # Sandbox
            28: {"crypto": "CRV", "color": "black", "category": "DeFi"},    # Curve
            29: {"crypto": "COMP", "color": "red", "category": "DeFi"},     # Compound
            30: {"crypto": "YFI", "color": "black", "category": "DeFi"},    # yearn.finance
            31: {"crypto": "SUSHI", "color": "red", "category": "DeFi"},    # SushiSwap
            32: {"crypto": "SNX", "color": "black", "category": "DeFi"},    # Synthetix
            33: {"crypto": "1INCH", "color": "red", "category": "DeFi"},    # 1inch
            34: {"crypto": "BAL", "color": "black", "category": "DeFi"},    # Balancer
            35: {"crypto": "REN", "color": "red", "category": "DeFi"},      # Ren
            36: {"crypto": "ZRX", "color": "black", "category": "DeFi"}     # 0x
        }

        # Payout multipliers
        self.payouts = {
            BetType.SINGLE_NUMBER: 35,      # 35:1 for single number
            BetType.RED_BLACK: 1,           # 1:1 for color
            BetType.EVEN_ODD: 1,            # 1:1 for even/odd
            BetType.HIGH_LOW: 1,            # 1:1 for high/low (1-18 vs 19-36)
            BetType.CRYPTO_CATEGORY: 5      # 5:1 for crypto category
        }

    async def create_game_session(
        self,
        user_id: str,
        client_seed: Optional[str] = None
    ) -> str:
        """Create a new game session."""
        async with AsyncSessionLocal() as session:
            try:
                # Generate provably fair seeds
                server_seed = secrets.token_hex(32)
                server_seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()

                if not client_seed:
                    client_seed = secrets.token_hex(16)

                # Create game session
                game_session = GameSession(
                    user_id=user_id,
                    server_seed=server_seed,
                    server_seed_hash=server_seed_hash,
                    client_seed=client_seed,
                    nonce=0
                )

                session.add(game_session)
                await session.commit()
                await session.refresh(game_session)

                return game_session.id

            except Exception as e:
                await session.rollback()
                raise e

    async def place_bet(
        self,
        game_session_id: str,
        user_id: str,
        bet_type: str,
        bet_value: str,
        amount: float
    ) -> Dict[str, Any]:
        """Place a bet in the game session."""
        # Import here to avoid circular dependency
        from gaming.round_manager import round_manager

        async with AsyncSessionLocal() as session:
            try:
                # Get current round_id from round manager
                current_round = round_manager.get_current_round()
                round_id = current_round["round_id"] if current_round else None

                # Validate that betting is allowed (must be in BETTING phase)
                if not current_round or current_round["phase"] != "betting":
                    return {
                        "success": False,
                        "error": "Betting is not allowed during this phase. Please wait for the next round."
                    }

                # Validate bet amount
                is_valid, message = await portfolio_manager.validate_bet_amount(user_id, amount)
                if not is_valid:
                    return {"success": False, "error": message}

                # Deduct bet amount from user's balance
                success = await portfolio_manager.deduct_gems(
                    user_id=user_id,
                    amount=amount,
                    transaction_type=TransactionType.BET_PLACED,
                    description=f"Roulette bet: {bet_type} on {bet_value}",
                    game_session_id=game_session_id
                )

                if not success:
                    return {"success": False, "error": "Failed to deduct bet amount"}

                # Create bet record with round_id
                bet = GameBet(
                    game_session_id=game_session_id,
                    user_id=user_id,
                    round_id=round_id,  # Link to current round
                    bet_type=bet_type,
                    bet_value=bet_value,
                    amount=amount
                )

                session.add(bet)
                await session.commit()
                await session.refresh(bet)

                # Register bet with round manager
                await round_manager.register_bet(bet.id, user_id)

                return {
                    "success": True,
                    "bet_id": bet.id,
                    "round_id": round_id,
                    "message": f"Bet placed: {amount} GEM on {bet_type} {bet_value}"
                }

            except Exception as e:
                await session.rollback()
                return {"success": False, "error": f"Error placing bet: {str(e)}"}

    async def spin_wheel(self, game_session_id: str) -> Dict[str, Any]:
        """Spin the roulette wheel and determine results."""
        async with AsyncSessionLocal() as session:
            try:
                # Get game session
                game_session = await session.get(GameSession, game_session_id)
                if not game_session:
                    return {"success": False, "error": "Game session not found"}

                if game_session.status != GameStatus.ACTIVE.value:
                    return {"success": False, "error": "Game session is not active"}

                # Generate result using provably fair method
                result = self._generate_provably_fair_result(
                    game_session.server_seed,
                    game_session.client_seed,
                    game_session.nonce
                )

                winning_number = result["number"]
                winning_data = self.crypto_wheel[winning_number]

                # Update game session with LAST spin results (for display purposes)
                game_session.winning_number = winning_number
                game_session.winning_crypto = winning_data["crypto"]
                game_session.winning_color = winning_data["color"]
                game_session.nonce += 1
                # CRITICAL FIX: Keep session ACTIVE for multiple rounds
                # Session should only be COMPLETED when user explicitly leaves/logs out
                # This allows players to spin multiple times without creating new sessions
                # game_session.status = GameStatus.COMPLETED.value  # REMOVED - stay ACTIVE
                # game_session.completed_at = datetime.utcnow()  # REMOVED

                # CRITICAL FIX: Only process bets that haven't been resolved yet
                # (is_winner is None means the bet hasn't been processed)
                # This prevents re-processing old bets from previous rounds
                bets_result = await session.execute(
                    select(GameBet).where(
                        GameBet.game_session_id == game_session_id,
                        GameBet.is_winner == None  # Only unresolved bets
                    )
                )
                bets = bets_result.scalars().all()
                print(f"[ROULETTE DEBUG] Found {len(bets)} unresolved bets to process for this spin")

                total_winnings = 0
                bet_results = []

                for bet in bets:
                    is_winner, multiplier, payout = self._calculate_bet_result(
                        bet, winning_number, winning_data
                    )

                    bet.is_winner = is_winner
                    bet.payout_multiplier = multiplier
                    bet.payout_amount = payout

                    if is_winner and payout > 0:
                        # Process winnings
                        await portfolio_manager.process_win(
                            user_id=bet.user_id,
                            amount=payout,
                            description=f"Roulette win: {bet.bet_type} on {bet.bet_value}",
                            game_session_id=game_session_id
                        )
                        total_winnings += payout
                    else:
                        # Record loss transaction
                        await portfolio_manager.deduct_gems(
                            user_id=bet.user_id,
                            amount=0,  # Already deducted when bet was placed
                            transaction_type=TransactionType.BET_LOST,
                            description=f"Roulette loss: {bet.bet_type} on {bet.bet_value}",
                            game_session_id=game_session_id
                        )

                    bet_results.append({
                        "bet_id": bet.id,
                        "bet_type": bet.bet_type,
                        "bet_value": bet.bet_value,
                        "amount": bet.amount,
                        "is_winner": is_winner,
                        "payout": payout,
                        "multiplier": multiplier
                    })

                # Update game session totals
                game_session.total_won = total_winnings
                game_session.total_bet = sum(bet.amount for bet in bets)
                game_session.total_lost = game_session.total_bet - total_winnings

                await session.commit()

                return {
                    "success": True,
                    "result": {
                        "number": winning_number,
                        "crypto": winning_data["crypto"],
                        "color": winning_data["color"],
                        "category": winning_data["category"]
                    },
                    "bets": bet_results,
                    "total_winnings": total_winnings,
                    "provably_fair": {
                        "server_seed_hash": game_session.server_seed_hash,
                        "client_seed": game_session.client_seed,
                        "nonce": game_session.nonce - 1
                    }
                }

            except Exception as e:
                await session.rollback()
                return {"success": False, "error": f"Error spinning wheel: {str(e)}"}

    def _generate_provably_fair_result(
        self,
        server_seed: str,
        client_seed: str,
        nonce: int
    ) -> Dict[str, Any]:
        """Generate provably fair result using seeds and nonce."""
        # Combine seeds with nonce
        combined_input = f"{server_seed}:{client_seed}:{nonce}"

        # Generate hash
        hash_result = hashlib.sha256(combined_input.encode()).hexdigest()

        # Convert first 8 characters of hash to number 0-36
        hex_substring = hash_result[:8]
        decimal_value = int(hex_substring, 16)
        winning_number = decimal_value % 37

        return {"number": winning_number}

    def _calculate_bet_result(
        self,
        bet: GameBet,
        winning_number: int,
        winning_data: Dict[str, str]
    ) -> Tuple[bool, float, float]:
        """Calculate if a bet wins and the payout amount."""
        bet_type = BetType(bet.bet_type)
        bet_value = bet.bet_value.lower()
        is_winner = False
        multiplier = 0.0

        print(f"[ROULETTE DEBUG] Checking bet: type={bet_type}, value='{bet_value}', amount={bet.amount}")
        print(f"[ROULETTE DEBUG] Winning: number={winning_number}, color='{winning_data['color']}', crypto={winning_data['crypto']}")

        if bet_type == BetType.SINGLE_NUMBER:
            if int(bet.bet_value) == winning_number:
                is_winner = True
                multiplier = self.payouts[bet_type]
                print(f"[ROULETTE DEBUG] ✓ SINGLE_NUMBER WIN! multiplier={multiplier}")

        elif bet_type == BetType.RED_BLACK:
            print(f"[ROULETTE DEBUG] RED_BLACK bet - comparing '{bet_value}' vs '{winning_data['color'].lower()}'")
            if winning_number != 0 and bet_value == winning_data["color"].lower():
                is_winner = True
                multiplier = self.payouts[bet_type]
                print(f"[ROULETTE DEBUG] ✓ RED_BLACK WIN! multiplier={multiplier}")

        elif bet_type == BetType.EVEN_ODD:
            if winning_number != 0:  # 0 is neither even nor odd for betting purposes
                is_even = winning_number % 2 == 0
                if (bet_value == "even" and is_even) or (bet_value == "odd" and not is_even):
                    is_winner = True
                    multiplier = self.payouts[bet_type]

        elif bet_type == BetType.HIGH_LOW:
            if winning_number != 0:
                is_high = winning_number >= 19
                if (bet_value == "high" and is_high) or (bet_value == "low" and not is_high):
                    is_winner = True
                    multiplier = self.payouts[bet_type]

        elif bet_type == BetType.CRYPTO_CATEGORY:
            if bet_value == winning_data["category"].lower():
                is_winner = True
                multiplier = self.payouts[bet_type]

        # Calculate payout (bet amount + winnings)
        payout = bet.amount * (multiplier + 1) if is_winner else 0.0

        return is_winner, multiplier, payout

    async def get_game_session(self, game_session_id: str) -> Optional[Dict[str, Any]]:
        """Get game session details."""
        async with AsyncSessionLocal() as session:
            game_session = await session.get(GameSession, game_session_id)
            if game_session:
                return game_session.to_dict()
            return None

    async def get_user_games(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's recent game sessions."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GameSession)
                .where(GameSession.user_id == user_id)
                .order_by(GameSession.started_at.desc())
                .limit(limit)
                .offset(offset)
            )
            games = result.scalars().all()
            return [game.to_dict() for game in games]

    def get_wheel_layout(self) -> Dict[int, Dict[str, str]]:
        """Get the complete wheel layout."""
        return self.crypto_wheel.copy()

    def get_bet_types(self) -> Dict[str, Any]:
        """Get available bet types and their payouts."""
        return {
            "single_number": {
                "name": "Single Number",
                "description": "Bet on a specific number (0-36)",
                "payout": f"{self.payouts[BetType.SINGLE_NUMBER]}:1",
                "example": "25"
            },
            "red_black": {
                "name": "Red/Black",
                "description": "Bet on red or black cryptocurrencies",
                "payout": f"{self.payouts[BetType.RED_BLACK]}:1",
                "example": "red"
            },
            "even_odd": {
                "name": "Even/Odd",
                "description": "Bet on even or odd numbers (0 excluded)",
                "payout": f"{self.payouts[BetType.EVEN_ODD]}:1",
                "example": "even"
            },
            "high_low": {
                "name": "High/Low",
                "description": "Bet on high (19-36) or low (1-18) numbers",
                "payout": f"{self.payouts[BetType.HIGH_LOW]}:1",
                "example": "high"
            },
            "crypto_category": {
                "name": "Crypto Category",
                "description": "Bet on cryptocurrency category",
                "payout": f"{self.payouts[BetType.CRYPTO_CATEGORY]}:1",
                "example": "defi"
            }
        }

# Global roulette engine instance
roulette_engine = CryptoRouletteEngine()