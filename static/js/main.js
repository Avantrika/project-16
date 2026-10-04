// SmartTrade Guard - Main UI Enhancements

document.addEventListener('DOMContentLoaded', () => {
    // 1. Highlight selected radio card option dynamically
    const radioCards = document.querySelectorAll('.radio-card');
    radioCards.forEach(card => {
        const radio = card.querySelector('input[type="radio"]');
        if (radio && radio.checked) {
            card.classList.add('selected');
        }

        card.addEventListener('click', () => {
            if (radio) {
                radio.checked = true;
                const name = radio.name;
                document.querySelectorAll(`input[name="${name}"]`).forEach(r => {
                    const parentCard = r.closest('.radio-card');
                    if (parentCard) parentCard.classList.remove('selected');
                });
                card.classList.add('selected');
                // Trigger change event for listeners
                radio.dispatchEvent(new Event('change'));
            }
        });
    });

    // 2. Demo Prefill URL parameter handler for new_trade
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('demo_prefill') === 'loss_chase') {
        const assetInput = document.getElementById('asset');
        const amountInput = document.getElementById('amount');
        const reasonInput = document.getElementById('reason');
        const plannedLossInput = document.getElementById('planned_loss');
        const emotionSelect = document.getElementById('emotion');
        const fomoSelect = document.getElementById('fomo_source');

        if (assetInput) assetInput.value = 'TATAMOTORS';
        if (amountInput) amountInput.value = '9500';
        if (plannedLossInput) plannedLossInput.value = '1500';
        if (reasonInput) reasonInput.value = 'Immediate recovery trade. Must recover ₹850 loss before 3:30 close.';
        if (emotionSelect) emotionSelect.value = 'Angry';
        if (fomoSelect) fomoSelect.value = 'Sudden price movement';
    }

    // 3. Dynamic Modified fields visibility in Feedback Screen
    const decisionRadios = document.querySelectorAll('input[name="decision"]');
    const modifySection = document.getElementById('modify-trade-section');
    const reasonSelect = document.getElementById('feedback-reason-select');

    if (decisionRadios.length > 0 && modifySection) {
        decisionRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked && radio.value === 'MODIFIED') {
                    modifySection.style.display = 'block';
                } else if (radio.checked) {
                    modifySection.style.display = 'none';
                }
                updateReasonOptions(radio.value);
            });
        });

        // Initialize based on default selected
        const selected = document.querySelector('input[name="decision"]:checked');
        if (selected) {
            if (selected.value === 'MODIFIED') modifySection.style.display = 'block';
            updateReasonOptions(selected.value);
        }
    }

    function updateReasonOptions(decision) {
        if (!reasonSelect) return;
        reasonSelect.innerHTML = '';

        let options = [];
        if (decision === 'CANCELLED') {
            options = [
                'I realized I was chasing a loss',
                'The amount was too high',
                'I noticed FOMO',
                'I was emotionally influenced',
                'I wanted to follow my rules',
                'Other'
            ];
        } else if (decision === 'MODIFIED') {
            options = [
                'Reduced risk',
                'Reduced amount',
                'Changed holding period',
                'Changed after reflection',
                'Other'
            ];
        } else {
            // CONTINUED
            options = [
                'Trade still matched my strategy',
                'I reviewed my risk',
                'I accepted the planned loss',
                'I was not influenced by FOMO',
                'Other'
            ];
        }

        options.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt;
            el.textContent = opt;
            reasonSelect.appendChild(el);
        });
    }
});
