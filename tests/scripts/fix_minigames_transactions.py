"""Fix minigames transaction to include balance_before and balance_after"""

with open('services/minigames_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix coinflip bet transaction
old_coinflip_bet = """        # Deduct bet amount
        wallet.gem_balance -= bet_amount

        # Create transaction for bet
        bet_transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.MINIGAME_BET.value,
            amount=-bet_amount,
            description=f"Coin Flip bet: {choice}"
        )
        db.add(bet_transaction)"""

new_coinflip_bet = """        # Capture balance before bet
        balance_before = wallet.gem_balance

        # Deduct bet amount
        wallet.gem_balance -= bet_amount

        # Create transaction for bet
        bet_transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.MINIGAME_BET.value,
            amount=-bet_amount,
            balance_before=balance_before,
            balance_after=wallet.gem_balance,
            description=f"Coin Flip bet: {choice}"
        )
        db.add(bet_transaction)"""

content = content.replace(old_coinflip_bet, new_coinflip_bet)

# Fix coinflip win transaction
old_coinflip_win = """        if won:
            payout = int(bet_amount * MiniGamesService.COINFLIP_MULTIPLIER)
            profit = payout - bet_amount
            wallet.gem_balance += payout

            # Create transaction for win
            win_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.MINIGAME_WIN.value,
                amount=payout,
                description=f"Coin Flip win: {result_flip}"
            )
            db.add(win_transaction)"""

new_coinflip_win = """        if won:
            payout = int(bet_amount * MiniGamesService.COINFLIP_MULTIPLIER)
            profit = payout - bet_amount

            # Capture balance before win payout
            balance_before_win = wallet.gem_balance
            wallet.gem_balance += payout

            # Create transaction for win
            win_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.MINIGAME_WIN.value,
                amount=payout,
                balance_before=balance_before_win,
                balance_after=wallet.gem_balance,
                description=f"Coin Flip win: {result_flip}"
            )
            db.add(win_transaction)"""

content = content.replace(old_coinflip_win, new_coinflip_win)

# Similar fixes for dice and higherlower - using generic pattern
# Fix all bet deductions
import re

# Pattern 1: Fix bet deductions
pattern1 = r'(# Get user wallet and check balance.*?if wallet\.gem_balance < bet_amount:\s+raise ValueError\("Insufficient GEM balance"\)\s+)(# Deduct bet amount\s+wallet\.gem_balance -= bet_amount\s+# Create transaction for bet\s+bet_transaction = Transaction\(\s+user_id=user_id,\s+transaction_type=TransactionType\.MINIGAME_BET\.value,\s+amount=-bet_amount,\s+description=f")(.*?)("\s+\)\s+db\.add\(bet_transaction\))'

def fix_bet(match):
    prefix = match.group(1)
    middle = match.group(2)
    desc = match.group(3)
    suffix = match.group(4)

    return f'''{prefix}# Capture balance before bet
        balance_before = wallet.gem_balance

        # Deduct bet amount
        wallet.gem_balance -= bet_amount

        # Create transaction for bet
        bet_transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.MINIGAME_BET.value,
            amount=-bet_amount,
            balance_before=balance_before,
            balance_after=wallet.gem_balance,
            description=f"{desc}{suffix}
        db.add(bet_transaction)'''

content = re.sub(pattern1, fix_bet, content, flags=re.DOTALL)

# Pattern 2: Fix win payouts (for dice and higherlower that weren't fixed yet)
pattern2 = r'(wallet\.gem_balance \+= payout\s+# Create transaction for win\s+win_transaction = Transaction\(\s+user_id=user_id,\s+transaction_type=TransactionType\.MINIGAME_WIN\.value,\s+amount=payout,\s+description=f")(.*?)("\s+\)\s+db\.add\(win_transaction\))'

def fix_win(match):
    prefix_desc = match.group(1)
    desc = match.group(2)
    suffix = match.group(3)

    return f'''# Capture balance before win payout
            balance_before_win = wallet.gem_balance
            wallet.gem_balance += payout

            # Create transaction for win
            win_transaction = Transaction(
                user_id=user_id,
                transaction_type=TransactionType.MINIGAME_WIN.value,
                amount=payout,
                balance_before=balance_before_win,
                balance_after=wallet.gem_balance,
                description=f"{desc}{suffix}
            db.add(win_transaction)'''

content = re.sub(pattern2, fix_win, content, flags=re.DOTALL)

with open('services/minigames_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed all minigames transactions to include balance_before and balance_after")
