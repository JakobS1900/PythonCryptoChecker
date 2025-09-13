from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from flask_socketio import emit
from ..models import db, Bet, Game, Transaction
from ..utils import get_current_balance
from ..auth.middleware import user_session_required
import random
import time

# Initialize blueprint
gaming_bp = Blueprint('gaming', __name__, url_prefix='/gaming')
active_games = {}

@gaming_bp.route('/roulette')
@login_required
@user_session_required
def roulette():
    """Render the roulette game page"""
    game_id = random.randint(100000, 999999)
    return render_template('roulette.html', 
                         game_id=game_id,
                         session={'gems': get_current_balance(current_user.id)})

def create_game():
    """Create a new roulette game"""
    game_id = random.randint(100000, 999999)
    game = Game(
        game_type='roulette',
        game_id=game_id,
        state='betting',
        start_time=time.time(),
        bet_phase_duration=20
    )
    db.session.add(game)
    db.session.commit()
    return game

# DISABLED: Conflicting route - replaced by api/gaming_api.py endpoint with demo mode support
# @gaming_bp.route('/api/roulette/place_bet', methods=['POST'])
# @login_required
# @user_session_required
# def place_bet():
#     """Place a bet on roulette"""
#     data = request.get_json()
#     if not data or 'type' not in data or 'value' not in data or 'amount' not in data:
#         return jsonify({'success': False, 'message': 'Missing required fields'}), 400
#     
#     bet_type = data['type']
#     bet_value = data['value']
#     amount = int(data['amount'])
#     
#     # Validate bet amount
#     if amount < 10 or amount > 10000:
#         return jsonify({'success': False, 'message': 'Invalid bet amount'}), 400
#     
#     # Check user balance
#     if current_user.gems < amount:
#         return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
#     
#     # Calculate multiplier based on bet type
#     multipliers = {
#         'number': 35,
#         'color': 14 if bet_value == 'green' else 2,
#         'parity': 2,
#         'range': 2
#     }
#     multiplier = multipliers.get(bet_type, 2)
#     
#     # Create bet record
#     bet = Bet(
#         user_id=current_user.id,
#         game_type='roulette',
#         bet_type=bet_type,
#         bet_value=bet_value,
#         amount=amount,
#         potential_win=amount * multiplier
#     )
#     
#     try:
#         db.session.add(bet)
#         # Deduct bet amount from user balance
#         current_user.gems -= amount
#         db.session.commit()
#         
#         # Record transaction
#         transaction = Transaction(
#             user_id=current_user.id,
#             type='bet',
#             amount=-amount,
#             description=f'Roulette bet: {amount} on {bet_value}',
#             balance=current_user.gems
#         )
#         db.session.add(transaction)
#         db.session.commit()
#         
#         # Notify client of balance update
#         emit('balance_update', {'balance': current_user.gems}, room=str(current_user.id))
#         
#         return jsonify({
#             'success': True,
#             'bet': {
#                 'id': bet.id,
#                 'type': bet.bet_type,
#                 'value': bet.bet_value,
#                 'amount': bet.amount,
#                 'potential_win': bet.potential_win
#             }
#         })
#         
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'success': False, 'message': 'Failed to place bet'}), 500

@gaming_bp.route('/api/roulette/spin', methods=['POST'])
@login_required
@user_session_required
def spin_roulette():
    """Process roulette spin and determine results"""
    # Get active bets for user
    bets = Bet.query.filter_by(
        user_id=current_user.id,
        game_type='roulette',
        resolved=False
    ).all()
    
    if not bets:
        return jsonify({'success': False, 'message': 'No active bets'}), 400
    
    # Generate result
    numbers = list(range(37))  # 0-36
    winning_number = random.choice(numbers)
    
    # Determine winning bets
    total_payout = 0
    bet_results = []
    
    for bet in bets:
        payout = 0
        won = False
        
        # Check if bet won based on type
        if bet.bet_type == 'number' and int(bet.bet_value) == winning_number:
            won = True
            payout = bet.amount * 35
        elif bet.bet_type == 'color':
            winning_color = 'green' if winning_number == 0 else (
                'red' if winning_number <= 7 else 'black'
            )
            if bet.bet_value == winning_color:
                won = True
                payout = bet.amount * (14 if winning_color == 'green' else 2)
        elif bet.bet_type == 'parity':
            if winning_number != 0:  # 0 is neither odd nor even
                is_even = winning_number % 2 == 0
                if (bet.bet_value == 'even' and is_even) or (bet.bet_value == 'odd' and not is_even):
                    won = True
                    payout = bet.amount * 2
        elif bet.bet_type == 'range':
            if bet.bet_value == '1-18' and 1 <= winning_number <= 18:
                won = True
                payout = bet.amount * 2
            elif bet.bet_value == '19-36' and 19 <= winning_number <= 36:
                won = True
                payout = bet.amount * 2
        
        total_payout += payout
        bet.resolved = True
        bet.won = won
        bet.payout = payout
        
        bet_results.append({
            'bet_type': bet.bet_type,
            'bet_value': bet.bet_value,
            'amount': bet.amount,
            'payout': payout,
            'won': won
        })
    
    # Update user balance and record transaction
    if total_payout > 0:
        current_user.gems += total_payout
        transaction = Transaction(
            user_id=current_user.id,
            type='win',
            amount=total_payout,
            description=f'Roulette win on {winning_number}',
            balance=current_user.gems
        )
        db.session.add(transaction)
    
    try:
        db.session.commit()
        
        # Notify client
        emit('balance_update', {'balance': current_user.gems}, room=str(current_user.id))
        
        return jsonify({
            'success': True,
            'number': winning_number,
            'payouts': bet_results,
            'total_payout': total_payout
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to process spin'}), 500
