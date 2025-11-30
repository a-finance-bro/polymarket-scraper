const API_BASE = '/api';

// Elements
const runBtn = document.getElementById('run-btn');
const modelSelect = document.getElementById('model-select');
const historySelect = document.getElementById('history-select');
const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const statusText = document.getElementById('status-text');
const resultsContainer = document.getElementById('results-container');
const opportunitiesList = document.getElementById('opportunities-list');
const tabBtns = document.querySelectorAll('.tab-btn');

let currentResults = [];
let activeTab = 'Real';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    fetchHistory();
    checkStatus();
    setInterval(checkStatus, 2000); // Poll status
});

// Event Listeners
runBtn.addEventListener('click', startArbitrage);
historySelect.addEventListener('change', (e) => {
    if (e.target.value) loadResults(e.target.value);
});
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeTab = btn.dataset.tab;
        renderResults();
    });
});

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/results`);
        const timestamps = await res.json();
        historySelect.innerHTML = '<option value="">Select a run...</option>';
        timestamps.forEach(ts => {
            const option = document.createElement('option');
            option.value = ts;
            option.textContent = ts;
            historySelect.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to fetch history:', e);
    }
}

async function startArbitrage() {
    const model = modelSelect.value;
    runBtn.disabled = true;
    try {
        await fetch(`${API_BASE}/run?model=${model}`, { method: 'POST' });
        progressContainer.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
    } catch (e) {
        alert('Failed to start job: ' + e.message);
        runBtn.disabled = false;
    }
}

async function checkStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`);
        const status = await res.json();

        if (status.is_running) {
            runBtn.disabled = true;
            progressContainer.classList.remove('hidden');
            progressFill.style.width = `${status.progress}%`;
            statusText.textContent = `${status.current_step} (${status.progress}%)`;
        } else {
            runBtn.disabled = false;
            if (status.progress === 100 && status.results_dir) {
                // Job just finished
                progressFill.style.width = '100%';
                statusText.textContent = 'Complete!';
                setTimeout(() => {
                    progressContainer.classList.add('hidden');
                    const timestamp = status.results_dir.split('_').pop();
                    loadResults(timestamp);
                    fetchHistory(); // Refresh dropdown
                }, 1000);
            }
        }
    } catch (e) {
        console.error('Status check failed:', e);
    }
}

async function loadResults(timestamp) {
    try {
        const res = await fetch(`${API_BASE}/results/${timestamp}`);
        const data = await res.json();
        currentResults = data.opportunities || [];
        resultsContainer.classList.remove('hidden');
        renderResults();
    } catch (e) {
        console.error('Failed to load results:', e);
    }
}

function renderResults() {
    opportunitiesList.innerHTML = '';

    const filtered = currentResults.filter(opp => opp.type === activeTab);

    if (filtered.length === 0) {
        opportunitiesList.innerHTML = '<p>No opportunities found for this category.</p>';
        return;
    }

    // Sort by profit potential (High > Medium > Low)
    const priority = { 'High': 3, 'Medium': 2, 'Low': 1 };
    filtered.sort((a, b) => priority[b.profit_potential] - priority[a.profit_potential]);

    filtered.forEach(opp => {
        const card = document.createElement('div');
        card.className = 'opportunity-card';

        const sourceClass = `source-${opp.source || 'LLM'}`;
        const profitClass = `profit-${opp.profit_potential}`;

        card.innerHTML = `
            <div class="opportunity-header">
                <span class="opportunity-type">${opp.type}</span>
                <div>
                    <span class="source-badge ${sourceClass}">${opp.source || 'LLM'}</span>
                    <span class="profit-badge ${profitClass}">${opp.profit_potential} Profit</span>
                </div>
            </div>
            <h3>${opp.market_title}</h3>
            <p>${opp.description}</p>
            <div class="confidence-meter">
                <div class="confidence-fill" style="width: ${opp.confidence * 100}%"></div>
            </div>
            <small>Confidence: ${(opp.confidence * 100).toFixed(0)}%</small>
            <div style="margin-top: 10px;">
                <button onclick="refreshOpportunity(this)" style="padding: 4px 8px; cursor: pointer;">Refresh</button>
            </div>
        `;
        opportunitiesList.appendChild(card);
    });
}

window.refreshOpportunity = async function (btn) {
    const originalText = btn.textContent;
    btn.textContent = 'Refreshing...';
    btn.disabled = true;
    // Mock refresh for now as backend endpoint isn't fully wired for single-item refresh yet
    await new Promise(r => setTimeout(r, 1000));
    btn.textContent = originalText;
    btn.disabled = false;
    alert('Refresh feature coming soon!');
};
