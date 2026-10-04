from datetime import datetime, time
import json
from config import Config
from database import get_db_connection

class BehavioralRiskEngine:
    def __init__(self, user_profile=None):
        self.weights = Config.RISK_WEIGHTS
        self.user_profile = user_profile

    def evaluate_trade(self, trade_data, recent_trades=None):
        """
        Runs comprehensive behavioral risk evaluation on a proposed trade.
        Returns a dict containing:
        - individual normalized factor scores (0-100)
        - weighted overall score (0-100)
        - risk_level ('LOW', 'MEDIUM', 'HIGH')
        - override_triggered (bool)
        - override_reason (str or None)
        - detected_patterns (list of str)
        - primary_concern (str)
        - cooling_off_recommended_seconds (int)
        - cooling_trigger_rule (str or None)
        """
        detected_patterns = []
        now = datetime.now()

        # Fetch recent trades if not provided
        if recent_trades is None:
            recent_trades = self._fetch_recent_trades(trade_data.get('user_id', 1))

        # 1. Financial Safety Override Check (Emergency / Borrowed Money)
        essential_flag = int(trade_data.get('essential_money_flag', 0))
        borrowed_flag = int(trade_data.get('borrowed_money_flag', 0))
        
        override_triggered = False
        override_reason = None

        if essential_flag == 1 or borrowed_flag == 1:
            override_triggered = True
            reasons = []
            if essential_flag == 1:
                reasons.append("essential/emergency funds")
            if borrowed_flag == 1:
                reasons.append("borrowed capital")
            override_reason = f"FINANCIAL SAFETY OVERRIDE: Proposed trade involves {' and '.join(reasons)}."
            detected_patterns.append(f"CRITICAL: User indicated trade is funded with {', '.join(reasons)}.")

        # 2. Factor A: Loss Chasing (30%)
        loss_chasing_score, loss_patterns = self._calc_loss_chasing(trade_data, recent_trades, now)
        detected_patterns.extend(loss_patterns)

        # 3. Factor B: Overtrading (20%)
        overtrading_score, overtrading_patterns = self._calc_overtrading(trade_data, recent_trades, now)
        detected_patterns.extend(overtrading_patterns)

        # 4. Factor C: FOMO / Hype (20%)
        fomo_score, fomo_patterns = self._calc_fomo(trade_data)
        detected_patterns.extend(fomo_patterns)

        # 5. Factor D: Risk Escalation (15%)
        escalation_score, escalation_patterns = self._calc_risk_escalation(trade_data, recent_trades)
        detected_patterns.extend(escalation_patterns)

        # 6. Factor E: Personal Rule Violation (10%)
        rule_score, rule_patterns = self._calc_rule_violation(trade_data, now)
        detected_patterns.extend(rule_patterns)

        # 7. Factor F: Emotional Signal (5%)
        emotion_score, emotion_patterns = self._calc_emotion(trade_data)
        detected_patterns.extend(emotion_patterns)

        # Calculate Weighted Overall Score (0 - 100)
        overall_score = (
            (loss_chasing_score * self.weights['loss_chasing']) +
            (overtrading_score * self.weights['overtrading']) +
            (fomo_score * self.weights['fomo']) +
            (escalation_score * self.weights['risk_escalation']) +
            (rule_score * self.weights['personal_rule']) +
            (emotion_score * self.weights['emotion'])
        )
        overall_score = round(min(100.0, max(0.0, overall_score)), 1)

        # Determine Risk Level & Cooling Off
        if override_triggered:
            risk_level = 'HIGH'
            cooling_seconds = Config.COOLING_OFF_EMERGENCY_SECONDS
            cooling_trigger = "Trigger 3: Emergency / Borrowed Capital Protection"
        elif overall_score >= 60.0:
            risk_level = 'HIGH'
            cooling_seconds, cooling_trigger = self._determine_cooling_trigger(
                recent_trades, trade_data, loss_chasing_score, overtrading_score, overall_score, now
            )
        elif overall_score >= 30.0:
            risk_level = 'MEDIUM'
            cooling_seconds = 0
            cooling_trigger = None
        else:
            risk_level = 'LOW'
            cooling_seconds = 0
            cooling_trigger = None

        # Synthesize Primary Concern
        primary_concern = self._formulate_primary_concern(
            override_triggered, loss_chasing_score, overtrading_score, fomo_score, escalation_score, rule_score, emotion_score
        )

        return {
            'loss_chasing_score': round(loss_chasing_score, 1),
            'overtrading_score': round(overtrading_score, 1),
            'fomo_score': round(fomo_score, 1),
            'risk_escalation_score': round(escalation_score, 1),
            'rule_violation_score': round(rule_score, 1),
            'emotion_score': round(emotion_score, 1),
            'overall_score': overall_score,
            'risk_level': risk_level,
            'override_triggered': 1 if override_triggered else 0,
            'override_reason': override_reason,
            'detected_patterns': detected_patterns,
            'primary_concern': primary_concern,
            'cooling_duration': cooling_seconds,
            'cooling_trigger': cooling_trigger
        }

    def _fetch_recent_trades(self, user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM trades 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 15
        ''', (user_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def _calc_loss_chasing(self, trade_data, recent_trades, now):
        score = 0.0
        patterns = []

        if not recent_trades:
            return score, patterns

        # Find the most recent non-cancelled trade
        last_trade = None
        for t in recent_trades:
            if t.get('status') in ['EXECUTED', 'MODIFIED']:
                last_trade = t
                break

        if not last_trade:
            return score, patterns

        # Check outcome of previous trade
        last_pl = float(last_trade.get('profit_loss') or 0.0)
        last_outcome = last_trade.get('outcome', '').upper()
        is_loss = (last_outcome == 'LOSS') or (last_pl < 0)

        if not is_loss:
            return 0.0, patterns

        # Calculate time delta in minutes
        try:
            trade_ts = datetime.strptime(str(last_trade['timestamp'])[:19], '%Y-%m-%d %H:%M:%S')
            delta_minutes = (now - trade_ts).total_seconds() / 60.0
        except Exception:
            delta_minutes = 15.0

        current_amount = float(trade_data.get('amount', 0.0))
        last_amount = float(last_trade.get('amount', 0.0))

        if delta_minutes <= Config.LOSS_CHASING_WINDOW_MINUTES:
            # Trade placed shortly after loss
            if current_amount > last_amount:
                # Direct Loss Chasing: Larger trade within 30 min of a loss
                ratio = current_amount / last_amount if last_amount > 0 else 1.5
                if ratio >= 1.5:
                    score = 95.0
                    patterns.append(f"Loss Chasing: New trade ₹{current_amount:,.0f} is {(ratio-1)*100:.0f}% larger than previous losing trade ₹{last_amount:,.0f} placed {int(delta_minutes)}m ago.")
                else:
                    score = 80.0
                    patterns.append(f"Loss Chasing: Increased position to ₹{current_amount:,.0f} shortly after a ₹{abs(last_pl):,.0f} loss ({int(delta_minutes)}m ago).")
            else:
                score = 50.0
                patterns.append(f"Rapid Re-entry: Placed new trade within {int(delta_minutes)}m of prior loss without adequate reset.")
        elif delta_minutes <= 60:
            score = 25.0
            patterns.append(f"Recent Loss Context: Prior trade ended in loss of ₹{abs(last_pl):,.0f} within past hour.")

        return min(100.0, score), patterns

    def _calc_overtrading(self, trade_data, recent_trades, now):
        score = 0.0
        patterns = []

        if not recent_trades:
            return score, patterns

        # Trades within 15 minutes
        trades_15m = 0
        trades_today = 0
        today_date = now.date()

        for t in recent_trades:
            try:
                ts = datetime.strptime(str(t['timestamp'])[:19], '%Y-%m-%d %H:%M:%S')
                if (now - ts).total_seconds() <= 15 * 60:
                    trades_15m += 1
                if ts.date() == today_date:
                    trades_today += 1
            except Exception:
                pass

        # Trigger check: 5 or more in 15 minutes
        if trades_15m >= 4:  # + current trade makes 5
            score = 95.0
            patterns.append(f"Overtrading Burst: {trades_15m + 1} trade attempts within the last 15 minutes.")
        elif trades_15m >= 2:
            score = 65.0
            patterns.append(f"Rapid Trading Frequency: {trades_15m + 1} orders placed within 15 minutes.")
        elif trades_15m == 1:
            score = 30.0

        # Daily limit check
        max_daily = 5
        if self.user_profile and 'max_daily_trades' in self.user_profile:
            max_daily = int(self.user_profile['max_daily_trades'])

        if (trades_today + 1) > max_daily:
            score = max(score, 75.0)
            patterns.append(f"Daily Frequency Exceeded: Attempt #{trades_today + 1} exceeds your configured daily limit of {max_daily} trades.")

        return min(100.0, score), patterns

    def _calc_fomo(self, trade_data):
        score = 0.0
        patterns = []
        source = trade_data.get('fomo_source', 'None')

        fomo_weights = {
            'Influencer': 90.0,
            'Social media': 85.0,
            'Market hype': 80.0,
            'Sudden price movement': 70.0,
            'Friends/others': 65.0,
            'None': 0.0,
            'My planned strategy': 0.0
        }

        score = fomo_weights.get(source, 20.0)

        if score >= 65.0:
            patterns.append(f"FOMO / External Influence: Decision influenced by '{source}'.")

        # Scan text reason for impulsive cues
        reason = str(trade_data.get('reason', '')).lower()
        hype_keywords = ['moon', 'rocket', 'recover quickly', 'cant miss', 'pump', 'all in', 'make back']
        for kw in hype_keywords:
            if kw in reason:
                score = min(100.0, score + 15.0)
                patterns.append(f"High-urgency language detected in trade thesis: '{kw}'.")
                break

        return min(100.0, score), patterns

    def _calc_risk_escalation(self, trade_data, recent_trades):
        score = 0.0
        patterns = []

        if not recent_trades or len(recent_trades) < 2:
            return score, patterns

        # Check progression of trade amounts after losses
        executed_trades = [t for t in recent_trades if t.get('status') in ['EXECUTED', 'MODIFIED']][:3]
        if not executed_trades:
            return score, patterns

        current_amount = float(trade_data.get('amount', 0.0))
        amounts = [current_amount] + [float(t.get('amount', 0.0)) for t in executed_trades]

        # Check if amounts are consistently increasing
        # e.g. T[2] < T[1] < T[0] (where 0 is current)
        if len(amounts) >= 3 and amounts[0] > amounts[1] > amounts[2]:
            score = 85.0
            patterns.append(f"Risk Escalation: 3 consecutive size increases (₹{amounts[2]:,.0f} → ₹{amounts[1]:,.0f} → ₹{amounts[0]:,.0f}).")
        elif len(amounts) >= 2 and amounts[0] >= (amounts[1] * 1.5):
            score = 65.0
            patterns.append(f"Size Escalation: Current trade size (₹{amounts[0]:,.0f}) is 50%+ higher than previous (₹{amounts[1]:,.0f}).")

        return min(100.0, score), patterns

    def _calc_rule_violation(self, trade_data, now):
        score = 0.0
        patterns = []

        profile = self.user_profile or {}
        safe_budget = float(profile.get('safe_budget', 10000.0))
        max_loss = float(profile.get('max_loss', 1000.0))
        hours_start = profile.get('preferred_hours_start', '09:15')
        hours_end = profile.get('preferred_hours_end', '15:30')

        current_amount = float(trade_data.get('amount', 0.0))
        planned_loss = float(trade_data.get('planned_loss', 0.0))

        # 1. Budget violation
        if current_amount > safe_budget:
            excess = current_amount - safe_budget
            score += 45.0
            patterns.append(f"Safe Budget Violation: Trade amount ₹{current_amount:,.0f} exceeds safe limit of ₹{safe_budget:,.0f} by ₹{excess:,.0f}.")

        # 2. Planned loss violation
        if planned_loss > max_loss:
            score += 40.0
            patterns.append(f"Loss Threshold Violation: Planned risk ₹{planned_loss:,.0f} exceeds your max allowed loss limit of ₹{max_loss:,.0f}.")

        # 3. Hours violation
        try:
            start_parts = [int(p) for p in hours_start.split(':')]
            end_parts = [int(p) for p in hours_end.split(':')]
            start_time = time(start_parts[0], start_parts[1])
            end_time = time(end_parts[0], end_parts[1])
            current_time = now.time()

            if not (start_time <= current_time <= end_time):
                score += 20.0
                patterns.append(f"Off-Hours Trading: Current time ({current_time.strftime('%H:%M')}) is outside preferred window ({hours_start} - {hours_end}).")
        except Exception:
            pass

        return min(100.0, score), patterns

    def _calc_emotion(self, trade_data):
        emotion = trade_data.get('emotion', 'Neutral')
        patterns = []

        emotion_map = {
            'Angry': 95.0,
            'Frustrated': 85.0,
            'Fearful': 75.0,
            'Anxious': 70.0,
            'Excited': 60.0,
            'Neutral': 20.0,
            'Confident': 10.0,
            'Calm': 0.0
        }

        score = emotion_map.get(emotion, 20.0)
        if score >= 60.0:
            patterns.append(f"Elevated Emotional State: Self-reported as '{emotion}'.")

        return score, patterns

    def _determine_cooling_trigger(self, recent_trades, trade_data, loss_chasing, overtrading, overall_score, now):
        """
        Concrete Trigger Matching from Requirement #10:
        Trigger 1: 3 losing trades in 30 mins + next trade amount larger -> 30-min cooling-off
        Trigger 2: 5 or more trades in 15 mins -> 15-min cooling-off
        Trigger 4: Multiple high-risk signals occurring together -> 30-min cooling-off
        Trigger 5: Trading after midnight combined with unusual behavior
        """
        # Check Trigger 2: Overtrading
        if overtrading >= 85.0:
            return Config.COOLING_OFF_OVERTRADING_SECONDS, "Trigger 2: Extreme Trading Frequency (Overtrading Burst)"

        # Check Trigger 1: 3 losing trades within 30 min + larger trade
        consecutive_losses = 0
        for t in recent_trades[:4]:
            if t.get('outcome') == 'LOSS' or float(t.get('profit_loss') or 0.0) < 0:
                consecutive_losses += 1
            else:
                break

        current_amount = float(trade_data.get('amount', 0.0))
        last_amount = float(recent_trades[0].get('amount', 0.0)) if recent_trades else 0.0

        if consecutive_losses >= 3 and current_amount > last_amount:
            return Config.COOLING_OFF_DEFAULT_SECONDS, "Trigger 1: 3 Consecutive Losses followed by Size Escalation"

        # Check Trigger 5: After midnight
        if now.hour < 5:
            return Config.COOLING_OFF_DEFAULT_SECONDS, "Trigger 5: High-Risk Off-Hours (Post-Midnight Impulse)"

        # Trigger 4: Multiple high-risk signals occurring together
        return Config.COOLING_OFF_DEFAULT_SECONDS, "Trigger 4: Compound Behavioural Risk Convergence"

    def _formulate_primary_concern(self, override, loss_chasing, overtrading, fomo, escalation, rule, emotion):
        if override:
            return "Financial Capital Risk: Use of essential or borrowed funds strictly demands emotional detachment."
        
        high_signals = []
        if loss_chasing >= 60:
            high_signals.append("loss-chasing")
        if fomo >= 60:
            high_signals.append("FOMO / social influence")
        if overtrading >= 60:
            high_signals.append("overtrading frequency")
        if escalation >= 60:
            high_signals.append("position escalation")
        if rule >= 60:
            high_signals.append("personal rule breach")
        if emotion >= 60:
            high_signals.append("heightened emotional tension")

        if not high_signals:
            return "Simulated trade aligns with typical risk parameters."
        elif len(high_signals) == 1:
            return f"Primary concern is {high_signals[0]}."
        else:
            return f"Multiple interacting concerns: {', '.join(high_signals[:-1])} and {high_signals[-1]}."
