'''
Simple example pokerbot, written in Python.
'''
from oddCalc import oddCalc
import pickle
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, BidAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot
import random
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_oddCalc(my_cards, board_cards, auction):
    return oddCalc(my_cards, board_cards, auction)
MULTIPLIER_DICT = {
    "won": [0.25, 0.5, 0.75, 1.0],
    "loss": [0.1, 0.25, 0.4, 0.5],
    "tie": [0.15, 0.3, 0.5, 0.65],
    "none": [0.2, 0.35, 0.55, 0.7]
}
class Player(Bot):
    '''
    A pokerbot.
    '''
    def is_small_blind(self, round_state, active):
        return round_state.button == active

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        pass

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        #my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        #game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        #round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        #my_cards = round_state.hands[active]  # your cards
        #big_blind = bool(active)  # True if you are the big blind
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        #my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        #previous_state = terminal_state.previous_state  # RoundState before payoffs
        #street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        #my_cards = previous_state.hands[active]  # your cards
        #opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed
        pass
    
    def did_we_win(self, my_bid, opponent_bid):
        my_bid_int = int(my_bid)
        opp_bid_int = int(opponent_bid)
        if my_bid_int > opp_bid_int:
            return "won"
        elif my_bid_int == opp_bid_int:
            return "tie"
        else:
            return "loss"

    def get_action(self, game_state, round_state, active):
        # Cache legal actions from round_state.
        legal_actions = round_state.legal_actions()
        can_bid   = BidAction   in legal_actions
        can_raise = RaiseAction in legal_actions
        can_call  = CallAction  in legal_actions
        can_check = CheckAction in legal_actions
        can_fold  = FoldAction  in legal_actions

        # Extract round parameters.
        street       = round_state.street
        my_cards     = round_state.hands[active]
        board_cards  = tuple(round_state.deck[:street])
        my_stack     = round_state.stacks[active]
        opp_stack    = round_state.stacks[1 - active]
        my_pip       = round_state.pips[active]
        opp_pip      = round_state.pips[1 - active]
        continue_cost = opp_pip - my_pip

        my_contribution  = STARTING_STACK - my_stack
        opp_contribution = STARTING_STACK - opp_stack
        pot_size = my_contribution + opp_contribution

        # Determine auction status (if street >= 4, the auction outcome is known).
        auction_status = "none"
        if street >= 4:
            auction_status = self.did_we_win(round_state.bids[active], round_state.bids[1 - active])

        # Calculate hand strength using the cached odd calculator.
        hand_strength = cached_oddCalc(tuple(my_cards), board_cards, auction_status)

        # Pre-flop fold condition for weak hands.
        if street == 0 and hand_strength < 0.34:
            if can_fold:
                return FoldAction()

        # Decide whether to bluff.
        bluffing = self.should_bluff(hand_strength, pot_size, round_state, active)

        # --- AUCTION PHASE (street == 3) ---
        if street == 3 and can_bid:
            bid_amount = self.determine_auction_bid(hand_strength, my_stack, opp_stack, pot_size)
            if bluffing:
                # When bluffing, use a modest multiplier.
                bid_amount = min(int(bid_amount * random.uniform(1.1, 1.2)), my_stack)
            return BidAction(bid_amount)

        # --- NORMAL BETTING ROUNDS ---
        if bluffing:
            if can_raise:
                min_raise, max_raise = round_state.raise_bounds()
                # Use 30% of stack (with a tight random range) for bluff bets.
                bluff_bet = min(int(0.3 * my_stack * random.uniform(1.1, 1.2)), my_stack)
                if bluff_bet >= min_raise:
                    return RaiseAction(min(bluff_bet, max_raise))
            if can_call:
                return CallAction()

        if continue_cost == 0:
            if can_check:
                return CheckAction()
            if can_raise and hand_strength > 0.65:
                min_raise, max_raise = round_state.raise_bounds()
                bet_size = self.calculate_optimal_bet(hand_strength, my_stack, pot_size, continue_cost, auction_status)
                if bet_size >= min_raise:
                    return RaiseAction(min(bet_size, max_raise))
            if can_check:
                return CheckAction()

        # Adjust thresholds dynamically based on pot odds.
        if continue_cost > 0.5 * pot_size:
            raise_threshold = 0.70
            call_threshold = 0.60
        else:
            raise_threshold = 0.65
            call_threshold = 0.55 if auction_status != "won" else 0.45

        # Adjust hand strength after auction. Use a bonus that scales with hand strength.
        if auction_status == "won":
            bonus = 1.1 + 0.1 * min(max(hand_strength - 0.4, 0), 0.6) / 0.6  # scales from 1.1 to 1.2
            hand_strength *= bonus
        elif auction_status == "loss":
            hand_strength *= 0.8

        if can_raise and hand_strength > raise_threshold:
            min_raise, max_raise = round_state.raise_bounds()
            bet_size = self.calculate_optimal_bet(hand_strength, my_stack, pot_size, continue_cost, auction_status)
            if bet_size >= min_raise:
                return RaiseAction(min(bet_size, max_raise))
        if can_call and (continue_cost <= 0.3 * my_stack or hand_strength > call_threshold):
            return CallAction()
        if can_fold and hand_strength < 0.4:
            return FoldAction()

        if can_check:
            return CheckAction()
        return FoldAction()

    def determine_auction_bid(self, hand_strength, my_stack, opp_stack, pot_size):
        if hand_strength >= 0.4:
            if(my_stack > opp_stack):
                return max(10, my_stack -5)
            else:
                return max(10, opp_stack - 5)
                
        else:
            base_bid = int(0.15 * my_stack)
            if opp_stack < my_stack:
                base_bid = max(base_bid - 5, 5)
            min_bid = 10
            bid = max(base_bid, min_bid) if base_bid > 0 else 0
            return min(bid, my_stack)

    def calculate_optimal_bet(self, hand_strength, my_stack, pot_size, continue_cost, auction_status):
        if continue_cost <= 0:
            return 0
        effective_pot = pot_size if auction_status != "won" else pot_size + 2 * continue_cost
        odds_ratio = effective_pot / continue_cost
        f = (hand_strength * (odds_ratio + 1) - 1) / odds_ratio
        f = max(0, min(f, 1))
        # Use smaller increments for aggressiveness and cap total aggressiveness.
        aggressiveness = 1.0
        if hand_strength > 0.3:
            aggressiveness += 0.05
        if hand_strength > 0.5:
            aggressiveness += 0.05
        if hand_strength > 0.7:
            aggressiveness += 0.05
        if hand_strength > 0.9:
            aggressiveness += 0.05
        aggressiveness = min(aggressiveness, 1.3)
        auction_multiplier = 1.2 if auction_status == "won" else (0.8 if auction_status == "loss" else 1.0)
        f *= aggressiveness * auction_multiplier
        # Use a tighter variance range to reduce erratic bets.
        variance = random.uniform(0.95, 1.05)
        bet = int(f * my_stack * variance)
        return max(0, min(bet, my_stack))

    def should_bluff(self, hand_strength, pot_size, round_state, active):
        """
        Returns True if we should bluff.
        
        This strategy uses:
          • Hand strength (only bluff with weak hands),
          • Pot size (a larger pot can justify a bluff),
          • Board texture (a dry board makes bluffing more credible),
          • Street information (later streets slightly favor bluffing).
        """
        # Only consider bluffing with a weak hand.
        if hand_strength > 0.4:
            return False

        # Base bluff probability.
        bluff_probability = 0.15

        # Increase bluff frequency if the pot is large.
        if pot_size > 0.5 * STARTING_STACK:
            bluff_probability += 0.1

        # Evaluate board texture.
        texture = self.board_texture_score(round_state.deck[:round_state.street])
        if texture < 0.3:
            bluff_probability += 0.1
        elif texture > 0.7:
            bluff_probability -= 0.1

        # Later streets add a slight bonus.
        if round_state.street >= 4:
            bluff_probability += 0.05

        return random.random() < bluff_probability

    def board_texture_score(self, board_cards):
        """
        Computes a simple board texture score between 0 and 1.
        Factors in suit concentration and sequential connectivity.
        """
        if not board_cards:
            return 0.0

        rank_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
                    "7": 7, "8": 8, "9": 9, "T": 10,
                    "J": 11, "Q": 12, "K": 13, "A": 14}
        ranks = []
        suits = []
        for card in board_cards:
            suit = card[-1]
            rank_str = card[:-1]
            rank = rank_map.get(rank_str, 0)
            ranks.append(rank)
            suits.append(suit)

        suit_counts = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        max_same_suit = max(suit_counts.values())
        suit_factor = (max_same_suit - 1) / (len(board_cards) - 1) if len(board_cards) > 1 else 0

        ranks.sort()
        sequence_count = 0
        for i in range(1, len(ranks)):
            if ranks[i] - ranks[i - 1] <= 2:
                sequence_count += 1
        sequence_factor = sequence_count / (len(ranks) - 1) if len(ranks) > 1 else 0

        texture = (suit_factor + sequence_factor) / 2
        return texture



if __name__ == '__main__':
    run_bot(Player(), parse_args())