import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from database import get_db_connection

class BehavioralAnalytics:
    def __init__(self, user_id=1):
        self.user_id = user_id

    def get_full_analytics(self):
        """
        Gathers all behavioral analytics, aggregates metrics, generates charts data,
        and constructs personal behavioral profile.
        """
        conn = get_db_connection()
        
        # Load trades dataframe
        trades_df = pd.read_sql_query('''
            SELECT t.*, r.loss_chasing_score, r.overtrading_score, r.fomo_score, 
                   r.risk_escalation_score, r.rule_violation_score, r.emotion_score,
                   r.overall_score, r.risk_level, r.override_triggered, r.detected_patterns
            FROM trades t
            LEFT JOIN risk_analysis r ON t.id = r.trade_id
            WHERE t.user_id = ?
            ORDER BY t.timestamp ASC
        ''', conn, params=(self.user_id,))

        # Load feedback dataframe
        feedback_df = pd.read_sql_query('''
            SELECT f.*, t.asset, t.amount, r.risk_level
            FROM feedback f
            JOIN trades t ON f.trade_id = t.id
            LEFT JOIN risk_analysis r ON t.id = r.trade_id
            WHERE t.user_id = ?
            ORDER BY f.timestamp ASC
        ''', conn, params=(self.user_id,))

        # Load user profile
        user_row = conn.execute('SELECT * FROM users WHERE id = ?', (self.user_id,)).fetchone()
        conn.close()

        user_profile = dict(user_row) if user_row else {}

        # 1. High Level Summary Metrics
        summary = self._calculate_summary_metrics(trades_df, feedback_df)

        # 2. Discipline Score (0-100, purely behavioral)
        discipline_score, discipline_breakdown = self._calculate_discipline_score(trades_df, feedback_df, user_profile)

        # 3. Intervention Effectiveness (Requirement 15)
        effectiveness = self._calculate_intervention_effectiveness(trades_df, feedback_df)

        # 4. Pattern Frequencies & Chart Data
        charts_data = self._generate_charts_data(trades_df, feedback_df)

        # 5. Recurring Behavioral Patterns (Requirement 18)
        recurring_patterns = self._detect_recurring_patterns(trades_df, feedback_df)

        # 6. Personal Behavioral Profile (Requirement 19)
        personal_profile = self._build_personal_profile(trades_df, feedback_df, recurring_patterns)

        # 7. Decision vs Outcome Journal Items (Requirement 17)
        journal_items = self._build_journal_items(trades_df)

        return {
            'summary': summary,
            'discipline_score': discipline_score,
            'discipline_breakdown': discipline_breakdown,
            'effectiveness': effectiveness,
            'charts_data': charts_data,
            'recurring_patterns': recurring_patterns,
            'personal_profile': personal_profile,
            'journal_items': journal_items
        }

    def _calculate_summary_metrics(self, trades_df, feedback_df):
        total_trades = len(trades_df)
        if total_trades == 0:
            return {
                'total_trades': 0, 'trades_today': 0, 'high_risk_count': 0,
                'avg_risk_score': 0, 'interventions_count': 0, 'cancelled_count': 0,
                'latest_risk_level': 'LOW', 'latest_risk_score': 0
            }

        # Date filtering for today
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        trades_today = trades_df[trades_df['timestamp'].str.startswith(today_str)] if not trades_df.empty else pd.DataFrame()

        high_risk_trades = trades_df[trades_df['risk_level'] == 'HIGH']
        interventions = trades_df[trades_df['risk_level'].isin(['MEDIUM', 'HIGH'])]

        cancelled = feedback_df[feedback_df['decision'] == 'CANCELLED'] if not feedback_df.empty else pd.DataFrame()

        latest_trade = trades_df.iloc[-1] if not trades_df.empty else None

        return {
            'total_trades': int(total_trades),
            'trades_today': int(len(trades_today)),
            'high_risk_count': int(len(high_risk_trades)),
            'avg_risk_score': round(float(trades_df['overall_score'].dropna().mean()), 1) if not trades_df.empty and not trades_df['overall_score'].dropna().empty else 0.0,
            'interventions_count': int(len(interventions)),
            'cancelled_count': int(len(cancelled)),
            'latest_risk_level': latest_trade['risk_level'] if latest_trade is not None and pd.notna(latest_trade['risk_level']) else 'LOW',
            'latest_risk_score': round(float(latest_trade['overall_score']), 1) if latest_trade is not None and pd.notna(latest_trade['overall_score']) else 0.0
        }

    def _calculate_discipline_score(self, trades_df, feedback_df, user_profile):
        """
        Discipline score is strictly behavioural, NOT tied to profit.
        Evaluates:
        1. Rule Adherence (Budget & Max Loss respect): 30 pts
        2. Intervention Compliance (Heeding Medium/High warnings): 30 pts
        3. Emotional Control (Avoiding extreme emotional states): 20 pts
        4. Strategy Focus (Avoiding FOMO/Hype triggers): 20 pts
        """
        if trades_df.empty:
            return 85.0, {
                'rule_adherence': 25, 'intervention_compliance': 25,
                'emotional_control': 18, 'strategy_focus': 17
            }

        # 1. Rule adherence
        rule_scores = trades_df['rule_violation_score'].dropna()
        avg_rule_violation = rule_scores.mean() if not rule_scores.empty else 0
        rule_pts = max(0.0, 30.0 - (avg_rule_violation / 100.0 * 30.0))

        # 2. Intervention compliance
        # Check decisions when warned
        risky_trades = trades_df[trades_df['risk_level'].isin(['MEDIUM', 'HIGH'])]
        if not risky_trades.empty and not feedback_df.empty:
            merged = pd.merge(risky_trades, feedback_df, left_on='id', right_on='trade_id', how='inner')
            if not merged.empty:
                favorable = merged['decision'].isin(['CANCELLED', 'MODIFIED']).sum()
                compliance_rate = favorable / len(merged)
                interv_pts = compliance_rate * 30.0
            else:
                interv_pts = 20.0
        else:
            interv_pts = 25.0

        # 3. Emotional control
        emotion_scores = trades_df['emotion_score'].dropna()
        avg_emotion = emotion_scores.mean() if not emotion_scores.empty else 20
        emotion_pts = max(0.0, 20.0 - (avg_emotion / 100.0 * 20.0))

        # 4. Strategy focus
        fomo_scores = trades_df['fomo_score'].dropna()
        avg_fomo = fomo_scores.mean() if not fomo_scores.empty else 0
        fomo_pts = max(0.0, 20.0 - (avg_fomo / 100.0 * 20.0))

        total_discipline = round(rule_pts + interv_pts + emotion_pts + fomo_pts, 1)
        total_discipline = min(100.0, max(15.0, total_discipline))

        return total_discipline, {
            'rule_adherence': round(rule_pts, 1),
            'intervention_compliance': round(interv_pts, 1),
            'emotional_control': round(emotion_pts, 1),
            'strategy_focus': round(fomo_pts, 1)
        }

    def _calculate_intervention_effectiveness(self, trades_df, feedback_df):
        """
        Requirement 15:
        Behaviour Changed = Cancelled + Modified + Delayed/Meaningfully reconsidered
        Effectiveness = Behaviour Changed / Total High-Risk Interventions * 100
        Clearly labeled as prototype behavioural metric.
        """
        if trades_df.empty or feedback_df.empty:
            return {
                'total_high_risk': 0, 'cancelled': 0, 'modified': 0,
                'continued': 0, 'behaviour_changed': 0, 'effectiveness_rate': 0.0,
                'status_label': 'Insufficient Data'
            }

        high_risk_trades = trades_df[trades_df['risk_level'] == 'HIGH']
        high_risk_ids = set(high_risk_trades['id'].tolist())

        if not high_risk_ids:
            # Look at all interventions if high-risk sample is small
            high_risk_trades = trades_df[trades_df['risk_level'].isin(['MEDIUM', 'HIGH'])]
            high_risk_ids = set(high_risk_trades['id'].tolist())

        fb_high = feedback_df[feedback_df['trade_id'].isin(high_risk_ids)]
        total_interventions = len(fb_high)

        if total_interventions == 0:
            return {
                'total_high_risk': 0, 'cancelled': 0, 'modified': 0,
                'continued': 0, 'behaviour_changed': 0, 'effectiveness_rate': 0.0,
                'status_label': 'Awaiting Interventions'
            }

        cancelled_count = int((fb_high['decision'] == 'CANCELLED').sum())
        modified_count = int((fb_high['decision'] == 'MODIFIED').sum())
        continued_count = int((fb_high['decision'] == 'CONTINUED').sum())

        behaviour_changed = cancelled_count + modified_count
        rate = round((behaviour_changed / total_interventions) * 100.0, 1)

        return {
            'total_high_risk': total_interventions,
            'cancelled': cancelled_count,
            'modified': modified_count,
            'continued': continued_count,
            'behaviour_changed': behaviour_changed,
            'effectiveness_rate': rate,
            'status_label': 'High Guard Efficacy' if rate >= 60 else 'Moderate Influence'
        }

    def _generate_charts_data(self, trades_df, feedback_df):
        """
        Prepares JSON-serializable chart data for Chart.js
        """
        # 1. Timeline of Risk Scores
        timeline_labels = []
        timeline_scores = []
        timeline_levels = []
        for _, row in trades_df.tail(10).iterrows():
            ts = str(row['timestamp'])
            timeline_labels.append(ts[5:16] if len(ts) >= 16 else ts)
            timeline_scores.append(float(row['overall_score']) if pd.notna(row['overall_score']) else 0.0)
            timeline_levels.append(row['risk_level'] or 'LOW')

        # 2. Factor Breakdown Averages
        factors = ['Loss Chasing', 'Overtrading', 'FOMO / Hype', 'Risk Escalation', 'Rule Violation', 'Emotion']
        avg_factor_scores = [
            float(trades_df['loss_chasing_score'].dropna().mean()) if not trades_df.empty and not trades_df['loss_chasing_score'].dropna().empty else 0.0,
            float(trades_df['overtrading_score'].dropna().mean()) if not trades_df.empty and not trades_df['overtrading_score'].dropna().empty else 0.0,
            float(trades_df['fomo_score'].dropna().mean()) if not trades_df.empty and not trades_df['fomo_score'].dropna().empty else 0.0,
            float(trades_df['risk_escalation_score'].dropna().mean()) if not trades_df.empty and not trades_df['risk_escalation_score'].dropna().empty else 0.0,
            float(trades_df['rule_violation_score'].dropna().mean()) if not trades_df.empty and not trades_df['rule_violation_score'].dropna().empty else 0.0,
            float(trades_df['emotion_score'].dropna().mean()) if not trades_df.empty and not trades_df['emotion_score'].dropna().empty else 0.0,
        ]
        avg_factor_scores = [round(x, 1) for x in avg_factor_scores]

        # 3. Decision Outcomes Distribution
        decisions_count = {'CANCELLED': 0, 'MODIFIED': 0, 'CONTINUED': 0}
        if not feedback_df.empty:
            counts = feedback_df['decision'].value_counts()
            for k in decisions_count:
                decisions_count[k] = int(counts.get(k, 0))

        # 4. Emotional Self-Reports
        emotions_list = ['Calm', 'Confident', 'Excited', 'Fearful', 'Angry', 'Frustrated', 'Anxious', 'Neutral']
        emotion_counts = {e: 0 for e in emotions_list}
        if not trades_df.empty and 'emotion' in trades_df:
            e_counts = trades_df['emotion'].value_counts()
            for e in emotions_list:
                emotion_counts[e] = int(e_counts.get(e, 0))

        # 5. FOMO Sources
        fomo_sources = ['My planned strategy', 'Social media', 'Influencer', 'Sudden price movement', 'Friends/others', 'Market hype', 'None']
        fomo_counts = {s: 0 for s in fomo_sources}
        if not trades_df.empty and 'fomo_source' in trades_df:
            s_counts = trades_df['fomo_source'].value_counts()
            for s in fomo_sources:
                fomo_counts[s] = int(s_counts.get(s, 0))

        return {
            'timeline': {'labels': timeline_labels, 'scores': timeline_scores, 'levels': timeline_levels},
            'radar_factors': {'labels': factors, 'scores': avg_factor_scores},
            'decisions': {'labels': ['Cancelled', 'Modified', 'Continued'], 'data': [decisions_count['CANCELLED'], decisions_count['MODIFIED'], decisions_count['CONTINUED']]},
            'emotions': {'labels': emotions_list, 'data': [emotion_counts[e] for e in emotions_list]},
            'fomo_sources': {'labels': fomo_sources, 'data': [fomo_counts[s] for s in fomo_sources]}
        }

    def _detect_recurring_patterns(self, trades_df, feedback_df):
        """
        Requirement 18: Use database records to identify repeated patterns
        e.g. Loss -> Short delay -> Larger trade
        FOMO related decisions and cancel rates
        """
        patterns = []

        if trades_df.empty:
            return patterns

        # 1. Loss Chasing Recurrence: Loss followed by larger trade
        loss_chasing_instances = 0
        trades_list = trades_df.to_dict('records')
        for i in range(1, len(trades_list)):
            prev = trades_list[i-1]
            curr = trades_list[i]
            prev_pl = float(prev.get('profit_loss') or 0.0)
            if prev.get('outcome') == 'LOSS' or prev_pl < 0:
                if float(curr.get('amount') or 0.0) > float(prev.get('amount') or 0.0):
                    loss_chasing_instances += 1

        if loss_chasing_instances > 0:
            patterns.append({
                'title': 'Loss → Short Delay → Escalated Position',
                'count': loss_chasing_instances,
                'description': f'Observed {loss_chasing_instances} instance(s) where trade size escalated immediately following a losing trade.',
                'severity': 'HIGH' if loss_chasing_instances >= 2 else 'MEDIUM',
                'action_recommendation': 'Enforce mandatory 30-minute cooling-off after any trade taking more than ₹500 in loss.'
            })

        # 2. FOMO Patterns
        fomo_trades = trades_df[trades_df['fomo_source'].isin(['Social media', 'Influencer', 'Market hype', 'Sudden price movement'])]
        fomo_count = len(fomo_trades)
        if fomo_count > 0:
            # Check how many were cancelled
            cancelled_fomo = 0
            if not feedback_df.empty:
                fomo_ids = set(fomo_trades['id'].tolist())
                fb_fomo = feedback_df[feedback_df['trade_id'].isin(fomo_ids)]
                cancelled_fomo = int((fb_fomo['decision'] == 'CANCELLED').sum())

            patterns.append({
                'title': 'FOMO & External Impulse Clustering',
                'count': fomo_count,
                'description': f'Identified {fomo_count} trades driven by social media, influencers, or hype. {cancelled_fomo} were successfully prevented by SmartTrade Guard intervention.',
                'severity': 'HIGH' if fomo_count >= 3 else 'MEDIUM',
                'action_recommendation': 'Require explicit written strategy checklist before allowing entries tagged with social media sources.'
            })

        # 3. Off-hours / Rapid Burst
        rapid_bursts = trades_df[trades_df['overtrading_score'] >= 60]
        if len(rapid_bursts) > 0:
            patterns.append({
                'title': 'High-Frequency Cluster / Overtrading Spurts',
                'count': len(rapid_bursts),
                'description': f'{len(rapid_bursts)} trades occurred during high-frequency execution clusters (>3 orders in rapid succession).',
                'severity': 'MEDIUM',
                'action_recommendation': 'Trigger 15-minute cool-down when 3 orders are placed within a 15-minute rolling window.'
            })

        return patterns

    def _build_personal_profile(self, trades_df, feedback_df, recurring_patterns):
        """
        Requirement 19: Personal Behaviour Profile using non-diagnostic language.
        - Primary Risk Pattern
        - Secondary Pattern
        - Most common trigger
        - Typical response
        - Recommended intervention
        """
        if trades_df.empty:
            return {
                'primary_pattern': 'Baseline Establishing',
                'secondary_pattern': 'Insufficient History',
                'most_common_trigger': 'Awaiting Live Simulated Data',
                'typical_response': 'Not yet determined',
                'recommended_intervention': 'Default 15-minute reflection on Medium/High risk'
            }

        # Calculate dominant risk components
        avgs = {
            'Loss Chasing': trades_df['loss_chasing_score'].dropna().mean() if not trades_df['loss_chasing_score'].dropna().empty else 0,
            'FOMO / External Hype': trades_df['fomo_score'].dropna().mean() if not trades_df['fomo_score'].dropna().empty else 0,
            'Overtrading': trades_df['overtrading_score'].dropna().mean() if not trades_df['overtrading_score'].dropna().empty else 0,
            'Risk Escalation': trades_df['risk_escalation_score'].dropna().mean() if not trades_df['risk_escalation_score'].dropna().empty else 0,
            'Rule Breaches': trades_df['rule_violation_score'].dropna().mean() if not trades_df['rule_violation_score'].dropna().empty else 0
        }
        sorted_patterns = sorted(avgs.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_patterns[0][0] if sorted_patterns[0][1] > 15 else 'Disciplined Strategy Adherence'
        secondary = sorted_patterns[1][0] if len(sorted_patterns) > 1 and sorted_patterns[1][1] > 10 else 'Minor Impulsivity'

        # Common trigger
        triggers = []
        if avgs['Loss Chasing'] > 20:
            triggers.append('Recent trading loss')
        if avgs['FOMO / External Hype'] > 20:
            triggers.append('Social media breakout calls / Hype')
        if avgs['Overtrading'] > 20:
            triggers.append('Intraday market volatility')
        most_common_trigger = ' & '.join(triggers) if triggers else 'Market opening volatility'

        # Typical response
        typical_response = 'Modifies or cancels trades upon intervention'
        if not feedback_df.empty:
            counts = feedback_df['decision'].value_counts()
            top_dec = counts.idxmax() if not counts.empty else 'CONTINUED'
            if top_dec == 'CANCELLED':
                typical_response = 'Cancels trade proactively when warning is presented'
            elif top_dec == 'MODIFIED':
                typical_response = 'Reduces size or modifies parameters after reflection'
            else:
                typical_response = 'Continues trade after required reflection period'

        recommended_interv = 'Mandatory 30-minute cooling-off + structured strategy verification' if primary in ['Loss Chasing', 'Risk Escalation'] else 'Pre-trade checklist & 15-minute pause on hype tags'

        return {
            'primary_pattern': primary,
            'secondary_pattern': secondary,
            'most_common_trigger': most_common_trigger,
            'typical_response': typical_response,
            'recommended_intervention': recommended_interv
        }

    def _build_journal_items(self, trades_df):
        """
        Requirement 17: Decision vs Outcome Analysis.
        Planned vs Actual comparison.
        Highlights if trade was profitable but had LOW discipline (reckless win).
        """
        items = []
        if trades_df.empty:
            return items

        # Take executed or modified trades with outcomes
        completed = trades_df[trades_df['status'].isin(['EXECUTED', 'MODIFIED', 'CANCELLED'])].tail(15)

        for _, row in completed.iterrows():
            pl = float(row.get('profit_loss') or 0.0)
            is_profit = pl > 0
            discipline = row.get('discipline_rating') or 'MODERATE'
            rule_score = float(row.get('rule_violation_score') or 0.0)

            # Special label for lucky bad trades
            is_lucky_gamble = is_profit and (discipline == 'LOW' or rule_score >= 50.0)

            items.append({
                'id': row['id'],
                'asset': row['asset'],
                'trade_type': row['trade_type'],
                'timestamp': str(row['timestamp'])[:16],
                'planned_amount': float(row.get('amount') or 0.0),
                'actual_amount': float(row.get('actual_amount') or row.get('amount') or 0.0),
                'planned_holding': row.get('holding_period') or 'Swing',
                'actual_holding': row.get('actual_holding_period') or row.get('holding_period') or 'Swing',
                'planned_loss': float(row.get('planned_loss') or 0.0),
                'planned_exit': float(row.get('planned_exit') or 0.0),
                'actual_exit': float(row.get('actual_exit') or 0.0),
                'profit_loss': pl,
                'outcome': row.get('outcome') or 'COMPLETED',
                'status': row.get('status'),
                'discipline_rating': discipline,
                'discipline_notes': row.get('discipline_notes') or 'Trade executed according to recorded parameters.',
                'is_lucky_gamble': is_lucky_gamble,
                'risk_level': row.get('risk_level') or 'LOW',
                'overall_score': float(row.get('overall_score') or 0.0)
            })

        items.reverse()  # Newest first
        return items
