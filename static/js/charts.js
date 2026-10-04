// SmartTrade Guard - Behavioral Charting Engine (Chart.js)

function initBehavioralCharts(data) {
    if (!data) return;

    // Common Chart Defaults
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.08)';

    // 1. Timeline Chart
    const ctxTimeline = document.getElementById('chartTimeline');
    if (ctxTimeline && data.timeline) {
        new Chart(ctxTimeline, {
            type: 'line',
            data: {
                labels: data.timeline.labels,
                datasets: [{
                    label: 'Risk Score (0-100)',
                    data: data.timeline.scores,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.15)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: data.timeline.scores.map(s => s >= 60 ? '#ef4444' : (s >= 30 ? '#f59e0b' : '#10b981')),
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 2. Risk Factors Radar
    const ctxRadar = document.getElementById('chartRadar');
    if (ctxRadar && data.radar_factors) {
        new Chart(ctxRadar, {
            type: 'radar',
            data: {
                labels: data.radar_factors.labels,
                datasets: [{
                    label: 'Factor Intensity',
                    data: data.radar_factors.scores,
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    borderColor: '#ef4444',
                    borderWidth: 2,
                    pointBackgroundColor: '#ef4444'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                        grid: { color: 'rgba(255, 255, 255, 0.08)' },
                        pointLabels: { color: '#cbd5e1', font: { size: 11, weight: '600' } },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 3. Decisions Donut
    const ctxDecisions = document.getElementById('chartDecisions');
    if (ctxDecisions && data.decisions) {
        new Chart(ctxDecisions, {
            type: 'doughnut',
            data: {
                labels: data.decisions.labels,
                datasets: [{
                    data: data.decisions.data,
                    backgroundColor: ['#10b981', '#6366f1', '#f59e0b'],
                    borderWidth: 0,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 16, boxWidth: 12 }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // 4. Emotional Self-Reports Bar Chart
    const ctxEmotions = document.getElementById('chartEmotions');
    if (ctxEmotions && data.emotions) {
        new Chart(ctxEmotions, {
            type: 'bar',
            data: {
                labels: data.emotions.labels,
                datasets: [{
                    label: 'Trade Frequency',
                    data: data.emotions.data,
                    backgroundColor: [
                        '#10b981', '#06b6d4', '#8b5cf6', '#f59e0b',
                        '#ef4444', '#dc2626', '#f97316', '#64748b'
                    ],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 5. FOMO Sources Bar
    const ctxFomo = document.getElementById('chartFomo');
    if (ctxFomo && data.fomo_sources) {
        new Chart(ctxFomo, {
            type: 'bar',
            data: {
                labels: data.fomo_sources.labels,
                datasets: [{
                    label: 'Trades Tagged',
                    data: data.fomo_sources.data,
                    backgroundColor: 'rgba(99, 102, 241, 0.75)',
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    y: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

window.initBehavioralCharts = initBehavioralCharts;
