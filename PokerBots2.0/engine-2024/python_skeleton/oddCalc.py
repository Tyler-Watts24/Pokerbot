import pickle
import os
import random
from itertools import combinations
from deuces import Card, Evaluator

PICKLE_FILE = 'allHandChances.pkl'
# Global mapping for simulation count based on the number of board cards.
SIMULATION_COUNTS = {0: 1000, 3: 200, 4: 500, 5: 400}

# Precompute card conversions so we don't call Card.new repeatedly.
CARD_CACHE = {
    f"{rank}{suit}": Card.new(f"{rank}{suit}")
    for suit in 'shdc' for rank in '23456789TJQKA'
}

# Build the full deck using the cached cards.
FULL_DECK = list(CARD_CACHE.values())

# Optionally, load precomputed odds once.
if os.path.exists(PICKLE_FILE):
    with open(PICKLE_FILE, 'rb') as file:
        PRECOMPUTED_ODDS = pickle.load(file)
else:
    PRECOMPUTED_ODDS = None

# Create a single Evaluator instance to reuse.
EVALUATOR = Evaluator()

def simulate_batch_optimized(simulations, available_cards, my_hand, my_board):
    """Optimized batch simulation without NumPy."""
    wins = 0
    opp_cards_needed = 2
    board_needed = 5 - len(my_board)
    extra_needed = opp_cards_needed + board_needed

    # No need to copy available_cards since random.sample does not modify it.
    for _ in range(simulations):
        drawn_cards = random.sample(available_cards, extra_needed)
        opponent_hand = drawn_cards[:opp_cards_needed]
        new_board = my_board + drawn_cards[opp_cards_needed:]

        my_score = EVALUATOR.evaluate(my_hand, new_board)
        opponent_score = EVALUATOR.evaluate(opponent_hand, new_board)

        # Increment wins if our score is lower (a better hand).
        wins += (my_score < opponent_score)
    return wins

def oddCalc(hand, board, auction, simulations=750):
    """Calculate odds of winning with a given hand and board state."""
    # Use precomputed odds for preflop if applicable.
    if auction == "none" and not board and PRECOMPUTED_ODDS is not None:
        return PRECOMPUTED_ODDS[tuple(sorted(hand))]

    # Select simulation count based on the board length if defined.
    simulations = SIMULATION_COUNTS.get(len(board), simulations)

    # Convert hand and board using the precomputed CARD_CACHE.
    my_hand = [CARD_CACHE[card] for card in hand[:2]]
    my_board = [CARD_CACHE[card] for card in board]

    # Build the set of used cards.
    used_cards = set(my_hand + my_board)
    # Filter the FULL_DECK using set difference.
    available_cards = [card for card in FULL_DECK if card not in used_cards]

    wins_total = simulate_batch_optimized(simulations, available_cards, my_hand, my_board)
    return wins_total / simulations

def generate_all_hands():
    """Generate all possible two-card starting hands."""
    ranks = '23456789TJQKA'
    suits = 'shdc'
    deck = [f"{rank}{suit}" for rank in ranks for suit in suits]
    return list(combinations(deck, 2))

def precompute_preflop_hands(simulations=10000):
    """Precompute and store preflop hand win probabilities."""
    preflop_odds = {}
    all_hands = generate_all_hands()

    for hand in all_hands:
        hand_key = tuple(sorted(hand))
        win_probability = oddCalc(hand, [], auction="simulate", simulations=simulations)
        preflop_odds[hand_key] = win_probability
        print(f"Computed {hand}: {win_probability:.4f}")

    with open(PICKLE_FILE, 'wb') as file:
        pickle.dump(preflop_odds, file)
    print("Preflop hand chances saved to", PICKLE_FILE)

# Uncomment the line below to precompute odds (run once, then comment it out).
# precompute_preflop_hands(simulations=10000)

#Tester
# Example hand and board:
'''
sample_hand = ['Ah', 'Kd']      # Ace of hearts and King of diamonds
sample_board = ['2c', '3d', '4h' ,"Ts", "7h"] # Flop: 2 of clubs, 3 of diamonds, 4 of hearts
auction_status = "simulate"      # Use any string except "none" to force simulation

# Call oddCalc and print the win probability.
win_probability = oddCalc(sample_hand, sample_board, auction_status)
print("Win probability:", win_probability)
'''