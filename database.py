import sqlite3
import json
from datetime import datetime, timedelta
import os
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        safe_budget REAL NOT NULL,
        max_loss REAL NOT NULL,
        preferred_hours_start TEXT DEFAULT '09:15',
        preferred_hours_end TEXT DEFAULT '15:30',
        preferred_holding_period TEXT DEFAULT 'Swing (2-5 Days)',
        max_daily_trades INTEGER DEFAULT 5,
        essential_money_flag INTEGER DEFAULT 0,
        borrowed_money_flag INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Trades Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        asset TEXT NOT NULL,
        trade_type TEXT NOT NULL,
        amount REAL NOT NULL,
        reason TEXT,
        holding_period TEXT,
        planned_exit REAL,
        planned_loss REAL,
        emotion TEXT NOT NULL,
        fomo_source TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'PENDING_RISK',
        outcome TEXT DEFAULT 'PENDING',
        profit_loss REAL DEFAULT 0.0,
        actual_exit REAL DEFAULT 0.0,
        actual_holding_period TEXT,
        actual_amount REAL,
        discipline_rating TEXT,
        discipline_notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Risk Analysis Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS risk_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id INTEGER NOT NULL,
        loss_chasing_score REAL NOT NULL,
        overtrading_score REAL NOT NULL,
        fomo_score REAL NOT NULL,
        risk_escalation_score REAL NOT NULL,
        rule_violation_score REAL NOT NULL,
        emotion_score REAL NOT NULL,
        overall_score REAL NOT NULL,
        risk_level TEXT NOT NULL,
        override_triggered INTEGER DEFAULT 0,
        override_reason TEXT,
        detected_patterns TEXT,
        primary_concern TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trade_id) REFERENCES trades (id)
    )
    ''')

    # Interventions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id INTEGER NOT NULL,
        intervention_type TEXT NOT NULL,
        cooling_duration INTEGER DEFAULT 0,
        trigger_rule TEXT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT DEFAULT 'ACTIVE',
        FOREIGN KEY (trade_id) REFERENCES trades (id)
    )
    ''')

    # Feedback Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id INTEGER NOT NULL,
        decision TEXT NOT NULL,
        reason TEXT NOT NULL,
        detailed_notes TEXT,
        amount_changed REAL,
        holding_period_changed TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trade_id) REFERENCES trades (id)
    )
    ''')

    conn.commit()
    conn.close()

def seed_sample_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] > 0:
        conn.close()
        return

    # 1. Insert Default User
    cursor.execute('''
    INSERT INTO users (
        name, safe_budget, max_loss, preferred_hours_start, preferred_hours_end,
        preferred_holding_period, max_daily_trades, essential_money_flag, borrowed_money_flag
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Alex Mercer', 10000.0, 1000.0, '09:15', '15:30', 'Swing (2-5 Days)', 5, 0, 0))
    user_id = cursor.lastrowid

    now = datetime.now()

    # Create realistic past historical trade events over the last 14 days
    # Showcase:
    # 1. Loss followed by FOMO & escalation
    # 2. Cancelled after FOMO warning (Intervention success)
    # 3. Profitable trade with LOW discipline (ignored risk limit but got lucky)
    # 4. Modified trade after Medium risk warning
    # 5. Overtrading cluster

    sample_trades_data = [
        # Trade 1: Disciplined win 10 days ago
        {
            'offset_days': 10, 'offset_minutes': 0,
            'asset': 'INFY', 'type': 'BUY', 'amount': 4000.0, 'reason': 'Clean technical breakout with support confirmation',
            'holding': 'Swing (2-5 Days)', 'exit': 1850.0, 'loss': 500.0, 'emotion': 'Calm', 'fomo': 'My planned strategy',
            'status': 'EXECUTED', 'outcome': 'PROFIT', 'pl': 650.0, 'actual_exit': 1860.0, 'actual_hold': 'Swing (2-5 Days)', 'actual_amt': 4000.0,
            'discipline': 'HIGH', 'discipline_notes': 'Strictly followed strategy, planned loss adhered to, exited on schedule.',
            'risk': {'loss_chasing': 0, 'overtrading': 0, 'fomo': 0, 'risk_escalation': 0, 'rule_violation': 0, 'emotion': 10, 'overall': 2, 'level': 'LOW', 'override': 0, 'patterns': ['Disciplined planned execution'], 'concern': 'No significant risk patterns.'},
            'intervention': {'type': 'ALLOW', 'duration': 0, 'trigger': 'None'},
            'feedback': {'decision': 'CONTINUED', 'reason': 'Trade still matched my strategy'}
        },
        # Trade 2: Loss 7 days ago
        {
            'offset_days': 7, 'offset_minutes': 120,
            'asset': 'TCS', 'type': 'BUY', 'amount': 5000.0, 'reason': 'Earnings run-up momentum',
            'holding': 'Intraday', 'exit': 4150.0, 'loss': 800.0, 'emotion': 'Confident', 'fomo': 'My planned strategy',
            'status': 'EXECUTED', 'outcome': 'LOSS', 'pl': -850.0, 'actual_exit': 3990.0, 'actual_hold': 'Intraday', 'actual_amt': 5000.0,
            'discipline': 'HIGH', 'discipline_notes': 'Accepted stop loss cleanly as pre-planned.',
            'risk': {'loss_chasing': 0, 'overtrading': 15, 'fomo': 0, 'risk_escalation': 0, 'rule_violation': 0, 'emotion': 15, 'overall': 5, 'level': 'LOW', 'override': 0, 'patterns': ['Within normal parameters'], 'concern': 'Controlled risk trade.'},
            'intervention': {'type': 'ALLOW', 'duration': 0, 'trigger': 'None'},
            'feedback': {'decision': 'CONTINUED', 'reason': 'Trade still matched my strategy'}
        },
        # Trade 3: FOMO attempt 5 days ago (Cancelled after intervention!)
        {
            'offset_days': 5, 'offset_minutes': 60,
            'asset': 'ZOMATO', 'type': 'BUY', 'amount': 8500.0, 'reason': 'Influencer video called for immediate 30% rally',
            'holding': 'Intraday', 'exit': 350.0, 'loss': 1200.0, 'emotion': 'Excited', 'fomo': 'Influencer',
            'status': 'CANCELLED', 'outcome': 'CANCELLED', 'pl': 0.0, 'actual_exit': 0.0, 'actual_hold': 'None', 'actual_amt': 0.0,
            'discipline': 'HIGH', 'discipline_notes': 'User listened to SmartTrade Guard warning and cancelled FOMO entry.',
            'risk': {'loss_chasing': 20, 'overtrading': 10, 'fomo': 85, 'risk_escalation': 30, 'rule_violation': 60, 'emotion': 70, 'overall': 48, 'level': 'MEDIUM', 'override': 0, 'patterns': ['Influencer-driven impulse', 'Planned loss exceeds ₹1,000 threshold'], 'concern': 'Social-media hype and excessive single-trade risk.'},
            'intervention': {'type': 'WARNING_REFLECTION', 'duration': 0, 'trigger': 'FOMO and Rule Violation'},
            'feedback': {'decision': 'CANCELLED', 'reason': 'I noticed FOMO'}
        },
        # Trade 4: Lucky Profit but POOR discipline 4 days ago
        {
            'offset_days': 4, 'offset_minutes': 90,
            'asset': 'RELIANCE', 'type': 'BUY', 'amount': 12500.0, 'reason': 'Market chatroom rumor on mega demerger',
            'holding': 'Swing (2-5 Days)', 'exit': 3100.0, 'loss': 2500.0, 'emotion': 'Excited', 'fomo': 'Market hype',
            'status': 'EXECUTED', 'outcome': 'PROFIT', 'pl': 2200.0, 'actual_exit': 3080.0, 'actual_hold': 'Intraday', 'actual_amt': 12500.0,
            'discipline': 'LOW', 'discipline_notes': 'User ignored safe budget (₹12.5k > ₹10k) and doubled max loss limit. Resulted in lucky profit, but decision process was reckless.',
            'risk': {'loss_chasing': 10, 'overtrading': 20, 'fomo': 80, 'risk_escalation': 60, 'rule_violation': 85, 'emotion': 75, 'overall': 52, 'level': 'MEDIUM', 'override': 0, 'patterns': ['Exceeded safe budget ₹10,000', 'Exceeded maximum loss ₹1,000', 'Market hype decision'], 'concern': 'Severe personal rule violations.'},
            'intervention': {'type': 'WARNING_REFLECTION', 'duration': 0, 'trigger': 'Budget and Loss Limit Violation'},
            'feedback': {'decision': 'CONTINUED', 'reason': 'Other'}
        },
        # Trade 5: Loss 2 days ago
        {
            'offset_days': 2, 'offset_minutes': 200,
            'asset': 'HDFCBANK', 'type': 'BUY', 'amount': 6000.0, 'reason': 'Breakdown pullback short',
            'holding': 'Intraday', 'exit': 1720.0, 'loss': 950.0, 'emotion': 'Frustrated', 'fomo': 'Sudden price movement',
            'status': 'EXECUTED', 'outcome': 'LOSS', 'pl': -980.0, 'actual_exit': 1660.0, 'actual_hold': 'Intraday', 'actual_amt': 6000.0,
            'discipline': 'MODERATE', 'discipline_notes': 'Slightly emotional entry after gap-down, but cut near planned loss.',
            'risk': {'loss_chasing': 15, 'overtrading': 25, 'fomo': 60, 'risk_escalation': 20, 'rule_violation': 10, 'emotion': 80, 'overall': 32, 'level': 'MEDIUM', 'override': 0, 'patterns': ['Emotional entry (Frustrated)', 'Chased sudden movement'], 'concern': 'Impulsive reaction to volatile candle.'},
            'intervention': {'type': 'WARNING_REFLECTION', 'duration': 0, 'trigger': 'Emotion and Price Chasing'},
            'feedback': {'decision': 'CONTINUED', 'reason': 'I accepted the planned loss'}
        },
        # Trade 6: High Risk Chasing & Modified after cooling-off 2 days ago (18 mins after Trade 5!)
        {
            'offset_days': 2, 'offset_minutes': 175,
            'asset': 'ICICIBANK', 'type': 'BUY', 'amount': 9500.0, 'reason': 'Need to recover HDFC loss before session close',
            'holding': 'Intraday', 'exit': 1250.0, 'loss': 1400.0, 'emotion': 'Angry', 'fomo': 'Sudden price movement',
            'status': 'MODIFIED', 'outcome': 'PROFIT', 'pl': 310.0, 'actual_exit': 1240.0, 'actual_hold': 'Intraday', 'actual_amt': 4000.0,
            'discipline': 'HIGH', 'discipline_notes': 'High-risk loss chasing flagged. During cooling-off, user chose to MODIFY and reduced trade size from ₹9,500 to ₹4,000.',
            'risk': {'loss_chasing': 90, 'overtrading': 50, 'fomo': 65, 'risk_escalation': 85, 'rule_violation': 70, 'emotion': 95, 'overall': 76, 'level': 'HIGH', 'override': 0, 'patterns': ['Loss chasing: Trade placed 18m after loss', 'Size escalated from ₹6,000 to ₹9,500', 'Angry emotional report'], 'concern': 'Loss-chasing and aggressive revenge trading.'},
            'intervention': {'type': 'MANDATORY_COOLING_OFF', 'duration': 1800, 'trigger': 'Loss chasing within 30m with larger position'},
            'feedback': {'decision': 'MODIFIED', 'reason': 'Reduced amount', 'amount_changed': 4000.0}
        },
        # Trade 7: Overtrading Burst Trade (Yesterday)
        {
            'offset_days': 1, 'offset_minutes': 90,
            'asset': 'TATAMOTORS', 'type': 'BUY', 'amount': 3500.0, 'reason': 'Breakout scalp attempt 3',
            'holding': 'Intraday', 'exit': 980.0, 'loss': 400.0, 'emotion': 'Anxious', 'fomo': 'Sudden price movement',
            'status': 'CANCELLED', 'outcome': 'CANCELLED', 'pl': 0.0, 'actual_exit': 0.0, 'actual_hold': 'None', 'actual_amt': 0.0,
            'discipline': 'HIGH', 'discipline_notes': 'Stopped trading after 15m cooling-off overtrading trigger.',
            'risk': {'loss_chasing': 40, 'overtrading': 85, 'fomo': 60, 'risk_escalation': 20, 'rule_violation': 80, 'emotion': 80, 'overall': 61, 'level': 'HIGH', 'override': 0, 'patterns': ['High trade frequency in past hour', 'Exceeded daily trade frequency guideline'], 'concern': 'Overtrading and cognitive fatigue.'},
            'intervention': {'type': 'MANDATORY_COOLING_OFF', 'duration': 900, 'trigger': 'Overtrading frequency limit exceeded'},
            'feedback': {'decision': 'CANCELLED', 'reason': 'I wanted to follow my rules'}
        },
        # Trade 8: Disciplined trade earlier today
        {
            'offset_days': 0, 'offset_minutes': 180,
            'asset': 'SBIN', 'type': 'BUY', 'amount': 4500.0, 'reason': 'Daily support trendline test with favorable 1:3 R:R',
            'holding': 'Swing (2-5 Days)', 'exit': 840.0, 'loss': 450.0, 'emotion': 'Calm', 'fomo': 'My planned strategy',
            'status': 'EXECUTED', 'outcome': 'LOSS', 'pl': -450.0, 'actual_exit': 805.0, 'actual_hold': 'Swing (2-5 Days)', 'actual_amt': 4500.0,
            'discipline': 'HIGH', 'discipline_notes': 'Execution adhered cleanly to trade book and max loss limit.',
            'risk': {'loss_chasing': 0, 'overtrading': 10, 'fomo': 0, 'risk_escalation': 0, 'rule_violation': 0, 'emotion': 10, 'overall': 3, 'level': 'LOW', 'override': 0, 'patterns': ['Calm planned strategy execution'], 'concern': 'Well-formed risk management.'},
            'intervention': {'type': 'ALLOW', 'duration': 0, 'trigger': 'None'},
            'feedback': {'decision': 'CONTINUED', 'reason': 'Trade still matched my strategy'}
        }
    ]

    for item in sample_trades_data:
        trade_time = now - timedelta(days=item['offset_days'], minutes=item['offset_minutes'])
        cursor.execute('''
        INSERT INTO trades (
            user_id, asset, trade_type, amount, reason, holding_period, planned_exit,
            planned_loss, emotion, fomo_source, timestamp, status, outcome, profit_loss,
            actual_exit, actual_holding_period, actual_amount, discipline_rating, discipline_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, item['asset'], item['type'], item['amount'], item['reason'],
            item['holding'], item['exit'], item['loss'], item['emotion'], item['fomo'],
            trade_time.strftime('%Y-%m-%d %H:%M:%S'), item['status'], item['outcome'],
            item['pl'], item['actual_exit'], item['actual_hold'], item['actual_amt'],
            item['discipline'], item['discipline_notes']
        ))
        trade_id = cursor.lastrowid

        r = item['risk']
        cursor.execute('''
        INSERT INTO risk_analysis (
            trade_id, loss_chasing_score, overtrading_score, fomo_score, risk_escalation_score,
            rule_violation_score, emotion_score, overall_score, risk_level, override_triggered,
            override_reason, detected_patterns, primary_concern, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_id, r['loss_chasing'], r['overtrading'], r['fomo'], r['risk_escalation'],
            r['rule_violation'], r['emotion'], r['overall'], r['level'], r['override'],
            None, json.dumps(r['patterns']), r['concern'], trade_time.strftime('%Y-%m-%d %H:%M:%S')
        ))

        inv = item['intervention']
        cursor.execute('''
        INSERT INTO interventions (
            trade_id, intervention_type, cooling_duration, trigger_rule, started_at, completed_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_id, inv['type'], inv['duration'], inv['trigger'],
            trade_time.strftime('%Y-%m-%d %H:%M:%S'),
            (trade_time + timedelta(seconds=inv['duration'])).strftime('%Y-%m-%d %H:%M:%S'),
            'COMPLETED'
        ))

        fb = item['feedback']
        amt_chg = fb.get('amount_changed', item['amount'])
        cursor.execute('''
        INSERT INTO feedback (
            trade_id, decision, reason, detailed_notes, amount_changed, holding_period_changed, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_id, fb['decision'], fb['reason'], 'Feedback recorded during simulated session',
            amt_chg, item['holding'], (trade_time + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        ))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_sample_data()
    print("Database initialized and sample behavioral data seeded successfully.")
