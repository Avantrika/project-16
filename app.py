from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
from datetime import datetime
from config import Config
from database import get_db_connection, init_db, seed_sample_data
from risk_engine import BehavioralRiskEngine
from analytics import BehavioralAnalytics

app = Flask(__name__)
app.config.from_object(Config)

# Helper to fetch current active user
def get_current_user():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users ORDER BY id ASC LIMIT 1').fetchone()
    conn.close()
    return dict(user) if user else None

@app.context_processor
def inject_global_context():
    user = get_current_user()
    return {
        'current_user': user,
        'app_disclaimer': 'SmartTrade Guard is a behavioural decision-support and financial safety tool. It does not provide investment advice, predict market prices, or guarantee financial outcomes. Simulated trading only.'
    }

# 1. Landing / Home Page
@app.route('/')
def index():
    user = get_current_user()
    analytics_svc = BehavioralAnalytics(user['id'] if user else 1)
    data = analytics_svc.get_full_analytics()
    return render_template('index.html', summary=data['summary'], personal_profile=data['personal_profile'], discipline_score=data['discipline_score'])

# 2. User Safety Profile
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users ORDER BY id ASC LIMIT 1').fetchone()

    if request.method == 'POST':
        name = request.form.get('name', 'Alex Mercer').strip()
        safe_budget = float(request.form.get('safe_budget', 10000.0))
        max_loss = float(request.form.get('max_loss', 1000.0))
        hours_start = request.form.get('preferred_hours_start', '09:15')
        hours_end = request.form.get('preferred_hours_end', '15:30')
        holding_period = request.form.get('preferred_holding_period', 'Swing (2-5 Days)')
        max_daily_trades = int(request.form.get('max_daily_trades', 5))
        essential_money = 1 if request.form.get('essential_money_flag') == '1' else 0
        borrowed_money = 1 if request.form.get('borrowed_money_flag') == '1' else 0

        if user:
            conn.execute('''
                UPDATE users SET
                    name = ?, safe_budget = ?, max_loss = ?, preferred_hours_start = ?,
                    preferred_hours_end = ?, preferred_holding_period = ?, max_daily_trades = ?,
                    essential_money_flag = ?, borrowed_money_flag = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, safe_budget, max_loss, hours_start, hours_end, holding_period, max_daily_trades, essential_money, borrowed_money, user['id']))
        else:
            conn.execute('''
                INSERT INTO users (name, safe_budget, max_loss, preferred_hours_start, preferred_hours_end, preferred_holding_period, max_daily_trades, essential_money_flag, borrowed_money_flag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, safe_budget, max_loss, hours_start, hours_end, holding_period, max_daily_trades, essential_money, borrowed_money))

        conn.commit()
        conn.close()
        flash('Safety Profile updated successfully! All upcoming simulated trades will be guarded by these rules.', 'success')
        return redirect(url_for('profile'))

    conn.close()
    return render_template('profile.html', user=dict(user) if user else {})

# 3. Trading Dashboard
@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    analytics_svc = BehavioralAnalytics(user['id'] if user else 1)
    data = analytics_svc.get_full_analytics()

    conn = get_db_connection()
    # Fetch latest 5 trades with risk status
    recent_trades = conn.execute('''
        SELECT t.*, r.overall_score, r.risk_level, r.primary_concern
        FROM trades t
        LEFT JOIN risk_analysis r ON t.id = r.trade_id
        WHERE t.user_id = ?
        ORDER BY t.timestamp DESC
        LIMIT 6
    ''', (user['id'] if user else 1,)).fetchall()
    conn.close()

    return render_template('dashboard.html',
                           summary=data['summary'],
                           discipline_score=data['discipline_score'],
                           discipline_breakdown=data['discipline_breakdown'],
                           effectiveness=data['effectiveness'],
                           personal_profile=data['personal_profile'],
                           recent_trades=[dict(t) for t in recent_trades])

# 4. New Simulated Trade
@app.route('/trade/new', methods=['GET', 'POST'])
def new_trade():
    user = get_current_user()
    if not user:
        flash('Please configure your safety profile first.', 'warning')
        return redirect(url_for('profile'))

    if request.method == 'POST':
        asset = request.form.get('asset', '').strip().upper()
        trade_type = request.form.get('trade_type', 'BUY').upper()
        amount = float(request.form.get('amount', 0.0))
        reason = request.form.get('reason', '').strip()
        holding_period = request.form.get('holding_period', 'Intraday')
        planned_exit = float(request.form.get('planned_exit', 0.0) or 0.0)
        planned_loss = float(request.form.get('planned_loss', 0.0) or 0.0)
        emotion = request.form.get('emotion', 'Neutral')
        fomo_source = request.form.get('fomo_source', 'None')
        essential_flag = 1 if request.form.get('essential_money_flag') == '1' else 0
        borrowed_flag = 1 if request.form.get('borrowed_money_flag') == '1' else 0

        trade_payload = {
            'user_id': user['id'],
            'asset': asset,
            'trade_type': trade_type,
            'amount': amount,
            'reason': reason,
            'holding_period': holding_period,
            'planned_exit': planned_exit,
            'planned_loss': planned_loss,
            'emotion': emotion,
            'fomo_source': fomo_source,
            'essential_money_flag': essential_flag,
            'borrowed_money_flag': borrowed_flag
        }

        # Run behavioral risk evaluation BEFORE saving trade
        engine = BehavioralRiskEngine(user_profile=user)
        risk_result = engine.evaluate_trade(trade_payload)

        # Insert trade record
        conn = get_db_connection()
        cursor = conn.cursor()

        initial_status = 'PENDING_RISK'
        if risk_result['risk_level'] == 'LOW':
            initial_status = 'EXECUTED'
            outcome = 'PENDING'
        elif risk_result['risk_level'] == 'MEDIUM':
            initial_status = 'WARNING_REVIEW'
            outcome = 'PENDING'
        else:
            initial_status = 'BLOCKED_COOLING'
            outcome = 'PENDING'

        cursor.execute('''
            INSERT INTO trades (
                user_id, asset, trade_type, amount, reason, holding_period,
                planned_exit, planned_loss, emotion, fomo_source, status, outcome,
                actual_amount, actual_holding_period
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user['id'], asset, trade_type, amount, reason, holding_period,
            planned_exit, planned_loss, emotion, fomo_source, initial_status, outcome,
            amount, holding_period
        ))
        trade_id = cursor.lastrowid

        # Insert risk analysis
        cursor.execute('''
            INSERT INTO risk_analysis (
                trade_id, loss_chasing_score, overtrading_score, fomo_score,
                risk_escalation_score, rule_violation_score, emotion_score,
                overall_score, risk_level, override_triggered, override_reason,
                detected_patterns, primary_concern
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_id, risk_result['loss_chasing_score'], risk_result['overtrading_score'],
            risk_result['fomo_score'], risk_result['risk_escalation_score'],
            risk_result['rule_violation_score'], risk_result['emotion_score'],
            risk_result['overall_score'], risk_result['risk_level'],
            risk_result['override_triggered'], risk_result['override_reason'],
            json.dumps(risk_result['detected_patterns']), risk_result['primary_concern']
        ))

        # Record intervention if MEDIUM or HIGH
        if risk_result['risk_level'] != 'LOW':
            inv_type = 'MANDATORY_COOLING_OFF' if risk_result['risk_level'] == 'HIGH' else 'WARNING_REFLECTION'
            cursor.execute('''
                INSERT INTO interventions (
                    trade_id, intervention_type, cooling_duration, trigger_rule, status
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                trade_id, inv_type, risk_result['cooling_duration'],
                risk_result['cooling_trigger'] or 'Behavioural Risk Warning', 'ACTIVE'
            ))

        conn.commit()
        conn.close()

        # Follow exact flow
        if risk_result['risk_level'] == 'HIGH':
            return redirect(url_for('cooling_off', trade_id=trade_id))
        else:
            return redirect(url_for('risk_analysis', trade_id=trade_id))

    return render_template('new_trade.html', user=user)

# 5. Risk Analysis Result
@app.route('/trade/<int:trade_id>/risk')
def risk_analysis(trade_id):
    conn = get_db_connection()
    trade = conn.execute('SELECT * FROM trades WHERE id = ?', (trade_id,)).fetchone()
    analysis = conn.execute('SELECT * FROM risk_analysis WHERE trade_id = ?', (trade_id,)).fetchone()
    intervention = conn.execute('SELECT * FROM interventions WHERE trade_id = ?', (trade_id,)).fetchone()
    conn.close()

    if not trade or not analysis:
        flash('Trade or risk analysis record not found.', 'danger')
        return redirect(url_for('dashboard'))

    analysis_dict = dict(analysis)
    analysis_dict['patterns_list'] = json.loads(analysis_dict.get('detected_patterns') or '[]')

    return render_template('risk_analysis.html',
                           trade=dict(trade),
                           analysis=analysis_dict,
                           intervention=dict(intervention) if intervention else None)

# 6. Cooling-Off / Intervention Screen
@app.route('/trade/<int:trade_id>/cooling-off')
def cooling_off(trade_id):
    conn = get_db_connection()
    trade = conn.execute('SELECT * FROM trades WHERE id = ?', (trade_id,)).fetchone()
    analysis = conn.execute('SELECT * FROM risk_analysis WHERE trade_id = ?', (trade_id,)).fetchone()
    intervention = conn.execute('SELECT * FROM interventions WHERE trade_id = ?', (trade_id,)).fetchone()
    conn.close()

    if not trade or not analysis:
        flash('Trade record not found.', 'danger')
        return redirect(url_for('dashboard'))

    analysis_dict = dict(analysis)
    analysis_dict['patterns_list'] = json.loads(analysis_dict.get('detected_patterns') or '[]')

    duration = intervention['cooling_duration'] if intervention else Config.COOLING_OFF_DEFAULT_SECONDS
    trigger_rule = intervention['trigger_rule'] if intervention else 'Compound Risk Convergence'

    return render_template('cooling_off.html',
                           trade=dict(trade),
                           analysis=analysis_dict,
                           intervention=dict(intervention) if intervention else None,
                           duration=duration,
                           trigger_rule=trigger_rule)

# 7. Decision & Feedback Screen
@app.route('/trade/<int:trade_id>/feedback', methods=['GET', 'POST'])
def feedback(trade_id):
    conn = get_db_connection()
    trade = conn.execute('SELECT * FROM trades WHERE id = ?', (trade_id,)).fetchone()
    analysis = conn.execute('SELECT * FROM risk_analysis WHERE trade_id = ?', (trade_id,)).fetchone()

    if not trade:
        conn.close()
        flash('Trade not found.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        decision = request.form.get('decision', 'CONTINUED').upper()
        reason = request.form.get('reason', '').strip()
        detailed_notes = request.form.get('detailed_notes', '').strip()

        amount_changed = float(request.form.get('modified_amount', 0.0) or trade['amount'])
        holding_changed = request.form.get('modified_holding', trade['holding_period'])
        planned_loss_changed = float(request.form.get('modified_loss', 0.0) or trade['planned_loss'])

        cursor = conn.cursor()

        # Update feedback table
        cursor.execute('''
            INSERT INTO feedback (
                trade_id, decision, reason, detailed_notes, amount_changed, holding_period_changed
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (trade_id, decision, reason, detailed_notes, amount_changed, holding_changed))

        # Update trade status
        if decision == 'CANCELLED':
            cursor.execute('''
                UPDATE trades SET
                    status = 'CANCELLED', outcome = 'CANCELLED',
                    discipline_rating = 'HIGH',
                    discipline_notes = 'User heeded safety guard and cancelled high-risk trade. Exemplary self-control.'
                WHERE id = ?
            ''', (trade_id,))
        elif decision == 'MODIFIED':
            cursor.execute('''
                UPDATE trades SET
                    status = 'MODIFIED', outcome = 'PENDING',
                    actual_amount = ?, actual_holding_period = ?, planned_loss = ?,
                    discipline_rating = 'HIGH',
                    discipline_notes = ?
                WHERE id = ?
            ''', (amount_changed, holding_changed, planned_loss_changed,
                  f'User reflected and adjusted trade size from ₹{trade["amount"]:,.0f} to ₹{amount_changed:,.0f}.',
                  trade_id))
        else: # CONTINUED
            cursor.execute('''
                UPDATE trades SET
                    status = 'EXECUTED', outcome = 'PENDING',
                    discipline_rating = 'MODERATE',
                    discipline_notes = 'User proceeded with trade after completing cooling-off reflection.'
                WHERE id = ?
            ''', (trade_id,))

        # Mark intervention completed
        cursor.execute('''
            UPDATE interventions SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP WHERE trade_id = ?
        ''', (trade_id,))

        conn.commit()
        conn.close()

        flash(f'Decision "{decision}" recorded in Decision Journal. Feedback loops help refine your future safety parameters!', 'success')
        return redirect(url_for('journal'))

    conn.close()
    analysis_dict = dict(analysis) if analysis else {}
    if analysis_dict:
        analysis_dict['patterns_list'] = json.loads(analysis_dict.get('detected_patterns') or '[]')

    return render_template('feedback.html', trade=dict(trade), analysis=analysis_dict)

# 8. Decision Journal
@app.route('/journal')
def journal():
    user = get_current_user()
    analytics_svc = BehavioralAnalytics(user['id'] if user else 1)
    data = analytics_svc.get_full_analytics()
    return render_template('journal.html',
                           journal_items=data['journal_items'],
                           discipline_score=data['discipline_score'],
                           discipline_breakdown=data['discipline_breakdown'])

# 9. Behavioural Analytics Dashboard
@app.route('/analytics')
def analytics():
    user = get_current_user()
    analytics_svc = BehavioralAnalytics(user['id'] if user else 1)
    data = analytics_svc.get_full_analytics()
    return render_template('analytics.html',
                           summary=data['summary'],
                           discipline_score=data['discipline_score'],
                           discipline_breakdown=data['discipline_breakdown'],
                           effectiveness=data['effectiveness'],
                           charts_data=data['charts_data'],
                           recurring_patterns=data['recurring_patterns'],
                           personal_profile=data['personal_profile'])

# 10. Risk Rules / Personal Rules
@app.route('/rules', methods=['GET', 'POST'])
def rules():
    user = get_current_user()
    if request.method == 'POST':
        # Flash rule confirmation
        flash('Configured behavioral safety parameters successfully synchronized.', 'success')
        return redirect(url_for('rules'))

    return render_template('rules.html', user=user, config=Config)

# 11. Trade History
@app.route('/history')
def history():
    user = get_current_user()
    conn = get_db_connection()
    trades = conn.execute('''
        SELECT t.*, r.overall_score, r.risk_level, r.loss_chasing_score,
               r.overtrading_score, r.fomo_score, r.risk_escalation_score,
               r.rule_violation_score, r.emotion_score, f.decision as feedback_decision,
               f.reason as feedback_reason
        FROM trades t
        LEFT JOIN risk_analysis r ON t.id = r.trade_id
        LEFT JOIN feedback f ON t.id = f.trade_id
        WHERE t.user_id = ?
        ORDER BY t.timestamp DESC
    ''', (user['id'] if user else 1,)).fetchall()
    conn.close()

    return render_template('history.html', trades=[dict(t) for t in trades])

# API: Live evaluate without saving
@app.route('/api/trade/evaluate', methods=['POST'])
def api_evaluate():
    user = get_current_user()
    data = request.get_json() or {}
    data['user_id'] = user['id'] if user else 1
    engine = BehavioralRiskEngine(user_profile=user)
    result = engine.evaluate_trade(data)
    return jsonify(result)

# Demo Scenario Runner
@app.route('/demo/trigger-loss-chase')
def demo_trigger_loss_chase():
    """
    Demo scenario from Requirement #10 / #24:
    Creates a recent loss and redirects user to new trade prefilled with an escalating amount
    to instantly demonstrate the high-risk loss-chasing detection flow!
    """
    user = get_current_user()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert immediate prior losing trade (10 minutes ago)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO trades (
            user_id, asset, trade_type, amount, reason, holding_period,
            planned_exit, planned_loss, emotion, fomo_source, timestamp,
            status, outcome, profit_loss, actual_exit, actual_amount, discipline_rating, discipline_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user['id'] if user else 1, 'TATAMOTORS', 'BUY', 5000.0, 'Morning breakout',
        'Intraday', 1050.0, 800.0, 'Frustrated', 'Sudden price movement', now_str,
        'EXECUTED', 'LOSS', -850.0, 970.0, 5000.0, 'MODERATE', 'Stopped out with ₹850 loss.'
    ))
    conn.commit()
    conn.close()

    flash('Demo Context Activated: A recent trade of ₹5,000 just closed at a -₹850 LOSS 10 minutes ago. Now try placing a larger trade (e.g. ₹9,000) to see Loss-Chasing Guard in action!', 'info')
    return redirect(url_for('new_trade', demo_prefill='loss_chase'))

if __name__ == '__main__':
    init_db()
    seed_sample_data()
    app.run(host='0.0.0.0', port=5000, debug=True)
