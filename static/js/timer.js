// SmartTrade Guard - Live Cooling-Off Countdown Engine

class CoolingOffTimer {
    constructor(durationSeconds, displayElementId, actionButtonId, statusElementId) {
        this.totalSeconds = parseInt(durationSeconds) || 1800;
        this.remainingSeconds = this.totalSeconds;
        this.displayElement = document.getElementById(displayElementId);
        this.actionButton = document.getElementById(actionButtonId);
        this.statusElement = document.getElementById(statusElementId);
        this.timerInterval = null;
        this.isCompleted = false;

        this.init();
    }

    init() {
        this.updateDisplay();
        if (this.actionButton) {
            this.actionButton.disabled = true;
            this.actionButton.classList.add('btn-secondary');
            this.actionButton.classList.remove('btn-primary');
        }

        this.timerInterval = setInterval(() => {
            this.tick();
        }, 1000);
    }

    tick() {
        if (this.remainingSeconds > 0) {
            this.remainingSeconds--;
            this.updateDisplay();
        } else {
            this.complete();
        }
    }

    updateDisplay() {
        const minutes = Math.floor(this.remainingSeconds / 60);
        const seconds = this.remainingSeconds % 60;
        const formatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

        if (this.displayElement) {
            this.displayElement.textContent = formatted;
        }

        if (this.statusElement && !this.isCompleted) {
            this.statusElement.textContent = `Mandatory cooling-off in progress. Reflection active.`;
        }
    }

    complete() {
        if (this.timerInterval) clearInterval(this.timerInterval);
        this.isCompleted = true;
        this.remainingSeconds = 0;

        if (this.displayElement) {
            this.displayElement.textContent = '00:00';
            this.displayElement.style.color = '#10b981';
            this.displayElement.style.textShadow = '0 0 20px rgba(16, 185, 129, 0.5)';
        }

        if (this.actionButton) {
            this.actionButton.disabled = false;
            this.actionButton.classList.remove('btn-secondary');
            this.actionButton.classList.add('btn-primary');
            this.actionButton.innerHTML = '<span>Proceed to Decision & Feedback →</span>';
        }

        if (this.statusElement) {
            this.statusElement.innerHTML = '<span style="color: #10b981; font-weight: 700;">✓ Cooling-off period completed. You may now reconsider your trade.</span>';
        }
    }

    fastForward(secondsRemaining = 3) {
        // Fast forward helper for evaluation/demo
        this.remainingSeconds = secondsRemaining;
        this.updateDisplay();
    }
}

window.CoolingOffTimer = CoolingOffTimer;
