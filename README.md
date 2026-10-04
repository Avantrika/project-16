# SmartTrade Guard 🛡️
### AI-Assisted Behavioural Decision & Financial Safety System for Simulated Trading

> **Disclaimer:** SmartTrade Guard is a behavioural decision-support and financial safety tool. It does **NOT** predict stock prices, does **NOT** recommend which stocks to buy or sell, and does **NOT** connect to live brokerages. It operates strictly on simulated trading to detect cognitive biases and protect traders from harmful execution habits.

---

## 1. Project Goal & Core Innovation

Most trading tools either provide price predictions or passive post-trade journals. **SmartTrade Guard is fundamentally different:** it is a **closed-loop pre-trade behavioural safety system** that intercepts harmful trading decisions **before execution**, explains the risk transparently, enforces cooling-off pauses, and records the trader's response to measure and improve intervention effectiveness.

### The Closed Feedback Loop

```text
DETECT
   ↓ (Loss Chasing, Overtrading, FOMO, Escalation, Rule Breaches)
EXPLAIN
   ↓ (Transparent 0-100 Factor Breakdown & Identified Patterns)
INTERVENE
   ↓ (Warning & Reflection or Mandatory Countdown Cooling-Off)
OBSERVE USER RESPONSE
   ↓ (Cancel Trade / Modify Trade / Continue After Reflection)
ASK WHY
   ↓ (Structured Feedback: "Why did you stop/change/continue?")
LEARN
   ↓ (Recurring Pattern Detector & Prototype Intervention Efficacy)
IMPROVE FUTURE INTERVENTION
```

---

## 2. Technology Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite
- **Data Processing:** Pandas, NumPy
- **Frontend:** HTML5, Modern CSS Design System (Glassmorphic cards, responsive sidebar, CSS variables, dark theme), Vanilla JavaScript
- **Interactive Visualizations:** Chart.js (Radar, Line timeline, Doughnut outcomes, Emotion & FOMO bars)
- **Cooling-Off Engine:** JavaScript countdown lock with fast-forward demo controls

---

## 3. Project Directory Structure

```text
project-16/
├── app.py                     # Main Flask Application & route controllers
├── config.py                  # Risk engine weights, thresholds, cooling durations
├── database.py                # SQLite schema creation, connection helpers, rich sample data
├── risk_engine.py             # Behavioral Risk Engine (Loss chasing, FOMO, Overtrading, Escalation, Overrides)
├── analytics.py               # Pandas-based behavioral profiling, recurring pattern detector, discipline score
├── requirements.txt           # Dependencies (Flask, Pandas, NumPy)
├── smarttrade.db              # SQLite Database (auto-generated on first run)
├── static/
│   ├── css/
│   │   └── style.css          # Sleek financial safety UI design system
│   └── js/
│       ├── main.js            # Dynamic form interactions, radio card highlights, demo prefill
│       ├── timer.js           # Live countdown timer & cooling-off lock engine
│       └── charts.js          # Chart.js behavioral dashboards (radar, timeline, donut, bars)
├── templates/
│   ├── base.html              # Layout with sidebar, safety banner, alerts
│   ├── index.html             # Page 1: Landing / Home page & System overview
│   ├── profile.html           # Page 2: User Safety Profile (budget, limits, hours, capital flags)
│   ├── dashboard.html         # Page 3: Trading Dashboard & live stats
│   ├── new_trade.html         # Page 4: Simulated Trading Entry Form
│   ├── risk_analysis.html     # Page 5: Risk Analysis Result & factor breakdown
│   ├── cooling_off.html       # Page 6: Mandatory Cooling-Off Screen with countdown timer
│   ├── feedback.html          # Page 7: Decision & Feedback Screen (Cancel/Modify/Continue + Ask Why)
│   ├── journal.html           # Page 8: Decision Journal (Planned vs Actual, discipline rating)
│   ├── analytics.html         # Page 9: Behavioural Analytics Dashboard (charts & patterns)
│   ├── rules.html             # Page 10: Risk Rules / Personal Rules configuration
│   └── history.html           # Page 11: Simulated Trade History table
├── tests/
│   └── test_risk_engine.py    # Unit tests for all individual risk rules, formulas, and overrides
└── README.md                  # Comprehensive documentation & demo walkthrough
```

---

## 4. Quick Start & Setup

### Prerequisites
- Python 3.10+ installed

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database & Run
```bash
python app.py
```

Open your browser at:
```text
http://127.0.0.1:5000/
```

*Note: On initial startup, the database is automatically created and seeded with realistic historical trade patterns (demonstrating disciplined wins, FOMO prevention, revenge trade scaling, and lucky reckless wins).*

---

## 5. Major Modules & Explanations

### `risk_engine.py` (Behavioral Risk Engine)
Evaluates proposed trades against 6 normalized dimensions (0–100):
1. **Loss Chasing (30% weight):** Detects if the prior trade was a loss, if the new trade is entered within 30 minutes, and if the trade size escalated.
2. **Overtrading (20% weight):** Detects rapid execution bursts (&ge;5 trades in 15 minutes) or daily frequency limit breaches.
3. **FOMO / Hype (20% weight):** Quantifies decision reliance on social media, finfluencers, chatrooms, or sudden price spikes.
4. **Risk Escalation (15% weight):** Detects consecutive order size increases after negative outcomes.
5. **Personal Rule Violation (10% weight):** Compares position size with safe budget and maximum acceptable loss limit.
6. **Emotional Signal (5% weight):** Incorporates self-reported tilt states (Angry, Frustrated, Fearful, Anxious).

**Weighted Formula:**
$$\text{Risk Score} = (L \times 0.30) + (O \times 0.20) + (F \times 0.20) + (E \times 0.15) + (R \times 0.10) + (S \times 0.05)$$

**Action Tiers:**
- **LOW (0–29):** Approved. Logged directly into Decision Journal.
- **MEDIUM (30–59):** Warning + Guided Reflection before reconsideration.
- **HIGH (60–100):** Mandatory Cooling-Off Countdown lock.

### Financial Safety Override (Section 9)
If the trader indicates that the trade uses **emergency/essential funds** or **borrowed money**, the system immediately triggers a **HIGH-RISK OVERRIDE** and mandates a 30-minute cooling-off period, completely bypassing the normal score formula.

### `analytics.py` (Behavioral Intelligence)
- **Discipline Score (0–100):** Measures rule adherence, intervention compliance, emotional composure, and strategy focus. **Critically, this score is independent of profit/loss!** A lucky trade that broke risk limits is graded as *Low Discipline*.
- **Intervention Effectiveness Metric (Prototype):**
  $$\text{Effectiveness} = \frac{\text{Cancelled} + \text{Modified}}{\text{Total High-Risk Interventions}} \times 100$$
- **Recurring Behaviour Detection:** Tracks recurring patterns such as *Loss &rarr; Short Delay &rarr; Escalated Position* across database history.
- **Personal Behaviour Profile:** Synthesizes non-diagnostic behavioral observations (Primary Risk Pattern, Secondary Pattern, Common Trigger, Typical Response).

### `static/js/timer.js` (Cooling-Off Engine)
Enforces a real-time JavaScript countdown timer. The "Proceed to Decision" button remains disabled and locked until the timer expires. Includes a **Fast-Forward (Demo Mode)** button for evaluators to test both the realistic countdown and the completed state instantly.

---

## 6. End-to-End Demo Scenario: High-Risk Loss-Chasing

To experience the closed feedback loop from start to finish:

1. **Trigger the Demo Shortcut:**
   - In the sidebar or on the Home page, click **⚡ Launch Demo Scenario** (or navigate to `/demo/trigger-loss-chase`).
   - This seeds an immediate prior trade in `TATAMOTORS` that closed at a **-₹850 loss** just 10 minutes ago, and pre-fills an escalated order.
2. **Submit the Escalated Order:**
   - On the New Trade form, observe:
     - Asset: `TATAMOTORS`
     - Position Size: `₹9,500` (escalated size compared to previous `₹5,000`)
     - Emotion: `Angry`
     - FOMO: `Sudden price movement`
     - Reason: *"Immediate recovery trade. Must recover ₹850 loss before 3:30 close."*
   - Click **Run Pre-Trade Risk Guard**.
3. **Inspect the Risk Analysis & Override:**
   - The Risk Engine flags **HIGH BEHAVIOURAL RISK (Score ~75–85/100)**.
   - Detected patterns highlight:
     - *Loss Chasing: New trade ₹9,500 is larger than previous losing trade ₹5,000 placed 10m ago.*
     - *Angry emotional state detected.*
     - *Chasing sudden price movement.*
   - SmartTrade Guard blocks immediate execution and activates **Mandatory Cooling-Off**.
4. **Mandatory Cooling-Off Countdown:**
   - View the active countdown clock (`29:59` counting down second-by-second).
   - Review the structured reflection prompts (*Are you trying to make back losses? Would you take this trade without FOMO?*).
   - Click **⚡ Fast-Forward Timer (Demo Mode)** in the top right to simulate the timer completion.
   - The countdown completes to `00:00` and unlocks the **Proceed to Decision & Feedback** button.
5. **Reconsideration & Closed-Loop Feedback:**
   - The user chooses what to do:
     - **Cancel Trade:** Select reason *"I realized I was chasing a loss"*.
     - Or **Modify Trade:** Scale down position to `₹3,000` with reason *"Reduced amount after reflection"*.
   - Click **Commit Decision to Journal**.
6. **Observe the Learning Dashboard:**
   - Navigate to **Decision Journal**: The trade is logged with high discipline praise for heeding the guard.
   - Navigate to **Behavioural Analytics**: Notice the **Intervention Effectiveness Metric** increase, the decision doughnut chart reflect the cancellation/modification, and the **Recurring Behaviour Detector** update.

---

## 7. Running Unit Tests

Run the full automated test suite for all risk engine rules:

```bash
python -m unittest discover tests -v
```

**Test Coverage:**
- `test_loss_chasing_detection`
- `test_overtrading_burst_detection`
- `test_fomo_influence_weights`
- `test_risk_escalation_progression`
- `test_personal_rule_violations`
- `test_emotional_signal_contributions`
- `test_financial_safety_override`
- `test_three_tier_risk_thresholds`

---

## 8. Summary of All 11 Application Pages

| # | Page | Route | Description |
|---|---|---|---|
| 1 | **Landing / Home** | `/` | System overview, closed-loop architecture, quick metric summary |
| 2 | **User Safety Profile** | `/profile` | Set safe budget, max loss, trading hours, essential/borrowed capital declarations |
| 3 | **Trading Dashboard** | `/dashboard` | Live risk level, discipline score, today's trades, recent surveillance stream |
| 4 | **New Simulated Trade** | `/trade/new` | Order inputs, emotion picker, FOMO sources, planned stop & exit |
| 5 | **Risk Analysis Result** | `/trade/<id>/risk` | Risk meter gauge, 6-factor weight breakdown, detected patterns, primary concern |
| 6 | **Cooling-Off Screen** | `/trade/<id>/cooling-off` | Live countdown timer, locked continue button, guided reflection prompts |
| 7 | **Decision & Feedback** | `/trade/<id>/feedback` | Reconsideration (Cancel/Modify/Continue) + structured "Ask Why" feedback |
| 8 | **Decision Journal** | `/journal` | Planned vs Actual comparison; flags lucky wins with poor discipline |
| 9 | **Behavioural Analytics** | `/analytics` | Radar charts, timeline, decision outcomes, recurring pattern detection, profile |
| 10 | **Risk Rules Engine** | `/rules` | View normalized formula weights, cooling triggers 1–5, tier thresholds |
| 11 | **Trade History** | `/history` | Full chronological audit log with filterable details and inspection links |

---

*SmartTrade Guard — Helping traders build unbreakable discipline before risking real capital.*
