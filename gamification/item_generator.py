"""
Collectible item generator for crypto-themed gamification system.
Creates trading cards, cosmetics, and special items.
"""

from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from database.unified_models import CollectibleItem, ItemType, ItemRarity
from logger import logger


class CryptoItemGenerator:
    """Generates crypto-themed collectible items for the gamification system."""
    
    def __init__(self):
        self.crypto_themes = [
            "bitcoin", "ethereum", "dogecoin", "cardano", "solana", "polygon",
            "chainlink", "litecoin", "avalanche", "polkadot", "cosmos", "algorand",
            "stellar", "vechain", "tezos", "monero", "zcash", "dash"
        ]
        
        self.rarity_colors = {
            ItemRarity.COMMON: "#9CA3AF",      # Gray
            ItemRarity.UNCOMMON: "#10B981",    # Green
            ItemRarity.RARE: "#3B82F6",       # Blue
            ItemRarity.EPIC: "#8B5CF6",       # Purple
            ItemRarity.LEGENDARY: "#F59E0B"    # Gold
        }
    
    async def generate_starter_items(self, session: AsyncSession) -> List[CollectibleItem]:
        """Generate initial set of collectible items for the platform."""
        items = []
        
        # Generate crypto trading cards
        items.extend(await self._generate_trading_cards())
        
        # Generate cosmetic items
        items.extend(await self._generate_cosmetics())
        
        # Generate achievement trophies
        items.extend(await self._generate_trophies())
        
        # Generate consumable items
        items.extend(await self._generate_consumables())
        
        # Generate special event items
        items.extend(await self._generate_special_items())
        
        # Add all items to database
        for item in items:
            session.add(item)
        
        await session.commit()
        
        logger.info(f"Generated {len(items)} collectible items")
        return items
    
    async def _generate_trading_cards(self) -> List[CollectibleItem]:
        """Generate crypto-themed trading cards."""
        cards = []
        
        # Common crypto cards (70% drop rate)
        common_cryptos = ["dogecoin", "litecoin", "stellar", "dash", "zcash"]
        for crypto in common_cryptos:
            card = CollectibleItem(
                name=f"{crypto.capitalize()} Card",
                description=f"A collectible trading card featuring {crypto.capitalize()}. Common rarity with basic design.",
                item_type=ItemType.TRADING_CARD.value,
                rarity=ItemRarity.COMMON.value,
                image_url=f"/assets/cards/{crypto}_common.png",
                color_theme=self.rarity_colors[ItemRarity.COMMON],
                gem_value=10.0,
                crypto_theme=crypto,
                effect_description="Display in your profile showcase"
            )
            cards.append(card)
        
        # Uncommon crypto cards (20% drop rate)
        uncommon_cryptos = ["cardano", "solana", "polygon", "chainlink", "avalanche"]
        for crypto in uncommon_cryptos:
            card = CollectibleItem(
                name=f"{crypto.capitalize()} Holographic Card",
                description=f"A shimmering holographic card featuring {crypto.capitalize()}. Enhanced visual effects.",
                item_type=ItemType.TRADING_CARD.value,
                rarity=ItemRarity.UNCOMMON.value,
                image_url=f"/assets/cards/{crypto}_uncommon.png",
                color_theme=self.rarity_colors[ItemRarity.UNCOMMON],
                animation_type="holographic",
                gem_value=50.0,
                crypto_theme=crypto,
                effect_description="Animated holographic display with particle effects"
            )
            cards.append(card)
        
        # Rare crypto cards (8% drop rate)
        rare_cryptos = ["polkadot", "cosmos", "algorand", "vechain", "tezos"]
        for crypto in rare_cryptos:
            card = CollectibleItem(
                name=f"{crypto.capitalize()} Crystal Card",
                description=f"A beautiful crystal-embedded card featuring {crypto.capitalize()}. Rare collector's item.",
                item_type=ItemType.TRADING_CARD.value,
                rarity=ItemRarity.RARE.value,
                image_url=f"/assets/cards/{crypto}_rare.png",
                color_theme=self.rarity_colors[ItemRarity.RARE],
                animation_type="crystal_glow",
                gem_value=200.0,
                crypto_theme=crypto,
                effect_description="Crystal glow animation with sound effects"
            )
            cards.append(card)
        
        # Epic crypto cards (1.8% drop rate)
        epic_cryptos = ["ethereum", "bitcoin"]
        for crypto in epic_cryptos:
            card = CollectibleItem(
                name=f"{crypto.capitalize()} Platinum Card",
                description=f"An ultra-premium platinum card featuring {crypto.capitalize()}. Epic rarity with premium effects.",
                item_type=ItemType.TRADING_CARD.value,
                rarity=ItemRarity.EPIC.value,
                image_url=f"/assets/cards/{crypto}_epic.png",
                color_theme=self.rarity_colors[ItemRarity.EPIC],
                animation_type="platinum_shine",
                gem_value=1000.0,
                crypto_theme=crypto,
                effect_description="Platinum shine with dynamic particle system and exclusive sound"
            )
            cards.append(card)
        
        # Legendary crypto card (0.2% drop rate)
        legendary_card = CollectibleItem(
            name="Satoshi's Genesis Card",
            description="The ultimate collectible - a legendary card commemorating the birth of cryptocurrency. Extremely rare and valuable.",
            item_type=ItemType.TRADING_CARD.value,
            rarity=ItemRarity.LEGENDARY.value,
            image_url="/assets/cards/genesis_legendary.png",
            color_theme=self.rarity_colors[ItemRarity.LEGENDARY],
            animation_type="legendary_aura",
            gem_value=5000.0,
            crypto_theme="bitcoin",
            effect_description="Legendary aura with rainbow particles, exclusive music, and screen effects"
        )
        cards.append(legendary_card)
        
        return cards
    
    async def _generate_cosmetics(self) -> List[CollectibleItem]:
        """Generate cosmetic items for avatar customization."""
        cosmetics = []
        
        # Avatar themes
        themes = [
            ("Crypto Bull", "bullish", ItemRarity.UNCOMMON, "Green bull-themed avatar with rising chart background"),
            ("Crypto Bear", "bearish", ItemRarity.UNCOMMON, "Red bear-themed avatar with falling chart background"),
            ("Diamond Hands", "diamond", ItemRarity.RARE, "Sparkling diamond hands avatar for true HODLers"),
            ("Rocket Moon", "rocket", ItemRarity.RARE, "To the moon! Rocket-themed space avatar"),
            ("Whale Trader", "whale", ItemRarity.EPIC, "Exclusive whale avatar for high-value traders"),
            ("Satoshi Style", "satoshi", ItemRarity.LEGENDARY, "Mysterious founder-inspired avatar theme")
        ]
        
        for name, theme_id, rarity, description in themes:
            cosmetic = CollectibleItem(
                name=f"{name} Avatar Theme",
                description=description,
                item_type=ItemType.COSMETIC.value,
                rarity=rarity.value,
                image_url=f"/assets/avatars/{theme_id}_theme.png",
                color_theme=self.rarity_colors[rarity],
                gem_value=self._get_gem_value_by_rarity(rarity),
                effect_description=f"Changes your avatar to {name.lower()} theme with unique animations"
            )
            cosmetics.append(cosmetic)
        
        # Profile backgrounds
        backgrounds = [
            ("Chart Green", "green_chart", ItemRarity.COMMON, "Green candlestick chart background"),
            ("Chart Red", "red_chart", ItemRarity.COMMON, "Red candlestick chart background"),
            ("Crypto Matrix", "matrix", ItemRarity.UNCOMMON, "Digital matrix rain with crypto symbols"),
            ("Neon City", "neon", ItemRarity.RARE, "Cyberpunk neon city backdrop"),
            ("Space Station", "space", ItemRarity.EPIC, "Futuristic space trading station"),
            ("Genesis Block", "genesis", ItemRarity.LEGENDARY, "The original Bitcoin genesis block visualization")
        ]
        
        for name, bg_id, rarity, description in backgrounds:
            background = CollectibleItem(
                name=f"{name} Background",
                description=description,
                item_type=ItemType.COSMETIC.value,
                rarity=rarity.value,
                image_url=f"/assets/backgrounds/{bg_id}_bg.png",
                color_theme=self.rarity_colors[rarity],
                gem_value=self._get_gem_value_by_rarity(rarity),
                effect_description=f"Sets your profile background to {name.lower()}"
            )
            cosmetics.append(background)
        
        return cosmetics
    
    async def _generate_trophies(self) -> List[CollectibleItem]:
        """Generate achievement trophy items."""
        trophies = []
        
        achievements = [
            ("First Spin Trophy", "first_spin", ItemRarity.COMMON, "Commemorates your first roulette spin"),
            ("Lucky Streak Trophy", "lucky_streak", ItemRarity.UNCOMMON, "Awarded for a 5-game winning streak"),
            ("Crypto Scholar Trophy", "crypto_scholar", ItemRarity.RARE, "For learning about 25 different cryptocurrencies"),
            ("High Roller Trophy", "high_roller", ItemRarity.EPIC, "For placing bets over 1000 GEM coins"),
            ("Legend Trophy", "legend", ItemRarity.LEGENDARY, "Ultimate achievement for platform mastery")
        ]
        
        for name, trophy_id, rarity, description in achievements:
            trophy = CollectibleItem(
                name=name,
                description=description,
                item_type=ItemType.TROPHY.value,
                rarity=rarity.value,
                image_url=f"/assets/trophies/{trophy_id}_trophy.png",
                color_theme=self.rarity_colors[rarity],
                gem_value=self._get_gem_value_by_rarity(rarity),
                is_tradeable=False,  # Trophies cannot be traded
                effect_description=f"Displays {name.lower()} in your trophy case"
            )
            trophies.append(trophy)
        
        return trophies
    
    async def _generate_consumables(self) -> List[CollectibleItem]:
        """Generate consumable items with temporary effects."""
        consumables = []
        
        consumable_items = [
            ("Lucky Charm", "lucky_charm", ItemRarity.UNCOMMON, "Increases drop rates by 25% for 1 hour", "+25% drop rate for 60 minutes"),
            ("XP Booster", "xp_boost", ItemRarity.RARE, "Doubles XP gains for 30 minutes", "2x experience points for 30 minutes"),
            ("GEM Multiplier", "gem_multi", ItemRarity.EPIC, "Increases GEM rewards by 50% for 1 hour", "+50% GEM coins for 60 minutes"),
            ("Golden Touch", "golden_touch", ItemRarity.LEGENDARY, "Next 5 games have guaranteed rare drops", "Guaranteed rare item drops for 5 games")
        ]
        
        for name, item_id, rarity, description, effect in consumable_items:
            consumable = CollectibleItem(
                name=name,
                description=description,
                item_type=ItemType.CONSUMABLE.value,
                rarity=rarity.value,
                image_url=f"/assets/consumables/{item_id}.png",
                color_theme=self.rarity_colors[rarity],
                gem_value=self._get_gem_value_by_rarity(rarity),
                is_consumable=True,
                effect_description=effect
            )
            consumables.append(consumable)
        
        return consumables
    
    async def _generate_special_items(self) -> List[CollectibleItem]:
        """Generate special event items."""
        special_items = []
        
        # Launch celebration items
        launch_items = [
            ("Beta Tester Badge", "beta_badge", ItemRarity.RARE, "Exclusive badge for beta testers", "Proof of early platform participation"),
            ("Founder's Coin", "founder_coin", ItemRarity.EPIC, "Special commemorative coin for early adopters", "Rare collector's item from platform launch"),
            ("Genesis NFT", "genesis_nft", ItemRarity.LEGENDARY, "Ultra-rare launch celebration NFT", "Unique digital collectible from day one")
        ]
        
        for name, item_id, rarity, description, effect in launch_items:
            special_item = CollectibleItem(
                name=name,
                description=description,
                item_type=ItemType.SPECIAL.value,
                rarity=rarity.value,
                image_url=f"/assets/special/{item_id}.png",
                color_theme=self.rarity_colors[rarity],
                gem_value=self._get_gem_value_by_rarity(rarity),
                is_tradeable=False,  # Special items are non-tradeable
                effect_description=effect
            )
            special_items.append(special_item)
        
        return special_items
    
    def _get_gem_value_by_rarity(self, rarity: ItemRarity) -> float:
        """Get GEM coin value based on item rarity."""
        return {
            ItemRarity.COMMON: 10.0,
            ItemRarity.UNCOMMON: 50.0,
            ItemRarity.RARE: 200.0,
            ItemRarity.EPIC: 1000.0,
            ItemRarity.LEGENDARY: 5000.0
        }[rarity]


async def initialize_collectible_items(session: AsyncSession):
    """Initialize the database with starter collectible items."""
    generator = CryptoItemGenerator()
    items = await generator.generate_starter_items(session)
    logger.info(f"Initialized {len(items)} collectible items in database")
    return items