from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from ..auth.middleware import user_session_required
from ..models import db, Bet, Game, User
from ..utils import emit_to_user
import random
import time

gaming_api = Blueprint('gaming_api', __name__)

# DISABLED: Conflicting route - replaced by api/gaming_api.py endpoint with demo mode support
# @gaming_api.route('/gaming/roulette/place_bet', methods=['POST'])
# @login_required
# @user_session_required
# def place_roulette_bet():
#     """Place a bet in the roulette game"""
#     data = request.get_json()
#     
#     if not data or 'color' not in data or 'amount' not in data:
#         return jsonify({'success': False, 'message': 'Missing required fields'}), 400
#     
#     color = data['color']
#     amount = int(data['amount'])
#     
#     # Validate color and amount
#     if color not in ['red', 'black', 'green']:
#         return jsonify({'success': False, 'message': 'Invalid color'}), 400
#         
#     if amount < 10 or amount > 10000:
#         return jsonify({'success': False, 'message': 'Invalid bet amount'}), 400
#         
#     # Check if user has enough GEMs
#     if current_user.gems < amount:
#         return jsonify({'success': False, 'message': 'Not enough GEMs'}), 400
#         
#     # Create and save bet
#     bet = Bet(
#         user_id=current_user.id,
#         game_type='roulette',
#         bet_type='color',
#         bet_value=color,
#         amount=amount
#     )
#     
#     # Calculate potential win
#     multiplier = 14 if color == 'green' else 2
#     bet.potential_win = amount * multiplier
#     
#     try:
#         db.session.add(bet)
#         # Deduct GEMs from user
#         current_user.gems -= amount
#         db.session.commit()
#         
#         # Update client
#         emit_to_user(current_user.id, 'gem_balance_update', {'new_balance': current_user.gems})
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

@gaming_api.route('/gaming/roulette/spin', methods=['POST'])
@login_required
@user_session_required
def spin_roulette():
    """Spin the roulette wheel and determine results"""
    # Get active bets for current user
    active_bets = Bet.query.filter_by(
        user_id=current_user.id,
        game_type='roulette',
        resolved=False
    ).all()
    
    if not active_bets:
        return jsonify({'success': False, 'message': 'No active bets'}), 400
        
    # Generate winning number
    numbers = [1, 14, 2, 13, 3, 12, 4, 0, 11, 5, 10, 6, 9, 7, 8]
    winning_number = random.choice(numbers)
    
    # Determine winning color
    if winning_number == 0:
        winning_color = 'green'
    elif winning_number <= 7:
        winning_color = 'red'
    else:
        winning_color = 'black'
        
    # Create game record
    game = Game(
        game_type='roulette',
        result=str(winning_number),
        timestamp=time.time()
    )
    
    try:
        db.session.add(game)
        
        # Process bets and calculate payouts
        payouts = []
        for bet in active_bets:
            payout = 0
            if bet.bet_value == winning_color:
                payout = bet.potential_win
                current_user.gems += payout
                
            payouts.append({
                'bet_type': bet.bet_type,
                'bet_value': bet.bet_value,
                'amount': payout
            })
            
            bet.resolved = True
            bet.payout = payout
            bet.game_id = game.id
            
        db.session.commit()
        
        # Notify client
        emit_to_user(current_user.id, 'gem_balance_update', {'new_balance': current_user.gems})
        
        return jsonify({
            'success': True,
            'number': winning_number,
            'color': winning_color,
            'payouts': payouts
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to process spin'}), 500
