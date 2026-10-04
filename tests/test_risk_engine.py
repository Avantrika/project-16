import unittest
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from risk_engine import BehavioralRiskEngine
from config import Config

class TestBehavioralRiskEngine(unittest.TestCase):

    def setUp(self):
        self.user_profile = {
            'id': 1,
            'name': 'Test Trader',
            'safe_budget': 10000.0,
            'max_loss': 1000.0,
            'preferred_hours_start': '09:15',
            'preferred_hours_end': '15:30',
            'max_daily_trades': 5
        }
        self.engine = BehavioralRiskEngine(user_profile=self.user_profile)

    def test_loss_chasing_detection(self):
        """Test Rule A: Loss followed quickly by larger trade triggers high loss chasing score."""
        now = datetime.now()
        recent_trades = [{
            'id': 10,
            'asset': 'INFY',
            'amount': 5000.0,
            'status': 'EXECUTED',
            'outcome': 'LOSS',
            'profit_loss': -800.0,
            'timestamp': (now - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
        }]

        # Proposed new trade: ₹9,000 (larger than ₹5,000) placed 10 mins after loss
        trade_data = {
            'asset': 'TCS',
            'amount': 9000.0,
            'planned_loss': 800.0,
            'emotion': 'Calm',
            'fomo_source': 'None'
        }

        result = self.engine.evaluate_trade(trade_data, recent_trades=recent_trades)
        self.assertGreaterEqual(result['loss_chasing_score'], 80.0)
        self.assertTrue(any('Loss Chasing' in p for p in result['detected_patterns']))

    def test_overtrading_burst_detection(self):
        """Test Rule B: 5 or more trades in 15 minutes triggers high overtrading score."""
        now = datetime.now()
        recent_trades = [
            {'id': i, 'amount': 2000.0, 'status': 'EXECUTED', 'timestamp': (now - timedelta(minutes=i*2)).strftime('%Y-%m-%d %H:%M:%S')}
            for i in range(1, 5)
        ]

        trade_data = {
            'asset': 'SBIN',
            'amount': 2000.0,
            'planned_loss': 300.0,
            'emotion': 'Calm',
            'fomo_source': 'None'
        }

        result = self.engine.evaluate_trade(trade_data, recent_trades=recent_trades)
        self.assertGreaterEqual(result['overtrading_score'], 85.0)
        self.assertTrue(any('Overtrading' in p for p in result['detected_patterns']))

    def test_fomo_influence_weights(self):
        """Test Rule C: Influencer and social media trigger high FOMO score."""
        trade_data_influencer = {
            'amount': 3000.0,
            'fomo_source': 'Influencer',
            'emotion': 'Calm'
        }
        res_inf = self.engine.evaluate_trade(trade_data_influencer, recent_trades=[])
        self.assertEqual(res_inf['fomo_score'], 90.0)

        trade_data_strategy = {
            'amount': 3000.0,
            'fomo_source': 'My planned strategy',
            'emotion': 'Calm'
        }
        res_strat = self.engine.evaluate_trade(trade_data_strategy, recent_trades=[])
        self.assertEqual(res_strat['fomo_score'], 0.0)

    def test_risk_escalation_progression(self):
        """Test Rule D: 3 consecutive size increases trigger escalation score."""
        recent_trades = [
            {'amount': 4000.0, 'status': 'EXECUTED'},
            {'amount': 2000.0, 'status': 'EXECUTED'}
        ]
        # Current amount 8000 -> 2000 -> 4000 -> 8000
        trade_data = {
            'amount': 8000.0,
            'planned_loss': 500.0,
            'emotion': 'Calm',
            'fomo_source': 'None'
        }

        result = self.engine.evaluate_trade(trade_data, recent_trades=recent_trades)
        self.assertGreaterEqual(result['risk_escalation_score'], 80.0)

    def test_personal_rule_violations(self):
        """Test Rule E: Exceeding safe budget and max loss triggers personal rule score."""
        # Safe budget is 10,000, Max loss is 1,000
        trade_data = {
            'amount': 15000.0,  # Exceeds budget
            'planned_loss': 2500.0,  # Exceeds max loss
            'emotion': 'Calm',
            'fomo_source': 'None'
        }

        result = self.engine.evaluate_trade(trade_data, recent_trades=[])
        self.assertGreaterEqual(result['rule_violation_score'], 80.0)
        self.assertTrue(any('Budget Violation' in p for p in result['detected_patterns']))
        self.assertTrue(any('Loss Threshold Violation' in p for p in result['detected_patterns']))

    def test_emotional_signal_contributions(self):
        """Test Rule F: Angry/Frustrated vs Calm states."""
        trade_angry = {'amount': 2000.0, 'emotion': 'Angry', 'fomo_source': 'None'}
        res_angry = self.engine.evaluate_trade(trade_angry, recent_trades=[])
        self.assertEqual(res_angry['emotion_score'], 95.0)

        trade_calm = {'amount': 2000.0, 'emotion': 'Calm', 'fomo_source': 'None'}
        res_calm = self.engine.evaluate_trade(trade_calm, recent_trades=[])
        self.assertEqual(res_calm['emotion_score'], 0.0)

    def test_financial_safety_override(self):
        """Test Section 9: Essential or borrowed money immediately overrides to HIGH risk."""
        # Even with calm emotion and planned strategy
        trade_data_essential = {
            'amount': 1000.0,
            'planned_loss': 100.0,
            'emotion': 'Calm',
            'fomo_source': 'My planned strategy',
            'essential_money_flag': 1
        }

        result = self.engine.evaluate_trade(trade_data_essential, recent_trades=[])
        self.assertEqual(result['risk_level'], 'HIGH')
        self.assertEqual(result['override_triggered'], 1)
        self.assertIn("FINANCIAL SAFETY OVERRIDE", result['override_reason'])

    def test_three_tier_risk_thresholds(self):
        """Test LOW (0-29), MEDIUM (30-59), and HIGH (60-100)."""
        # Low risk trade
        low_trade = {'amount': 2000.0, 'planned_loss': 200.0, 'emotion': 'Calm', 'fomo_source': 'None'}
        res_low = self.engine.evaluate_trade(low_trade, recent_trades=[])
        self.assertEqual(res_low['risk_level'], 'LOW')

        # Medium risk trade:
        # e.g. FOMO (Influencer=90 -> 18 pts) + Rule violation (Amount 15k > 10k and Loss 1.5k > 1k = 85 -> 8.5 pts) + Emotion (Frustrated = 85 -> 4.25 pts) = 30.75 pts -> MEDIUM
        med_trade = {'amount': 15000.0, 'planned_loss': 1500.0, 'emotion': 'Frustrated', 'fomo_source': 'Influencer'}
        res_med = self.engine.evaluate_trade(med_trade, recent_trades=[])
        self.assertEqual(res_med['risk_level'], 'MEDIUM')

if __name__ == '__main__':
    unittest.main()
