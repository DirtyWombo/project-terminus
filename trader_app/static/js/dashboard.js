document.addEventListener('DOMContentLoaded', function () {
    const API_ENDPOINTS = {
        portfolioSummary: '/api/portfolio/summary',
        status: '/api/status',
        tokenDetails: '/api/token_details/',
        journal: '/api/journal',
        speculativeAnalysis: '/api/speculative_analysis/',
    };

    let portfolioChart = null;

    /**
     * Fetches data from a given API endpoint.
     * @param {string} endpoint - The API endpoint to fetch from.
     * @returns {Promise<Object>} A promise that resolves to the JSON data.
     */
    async function fetchData(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching from ${endpoint}:`, error);
            // Return a default structure on error to prevent UI crashes
            return null;
        }
    }

    /**
     * Fetches token details for a given symbol.
     * @param {string} symbol - The cryptocurrency symbol (e.g., BTC-USD).
     * @returns {Promise<Object>} A promise that resolves to the token details.
     */
    async function fetchTokenDetails(symbol) {
        return fetchData(`${API_ENDPOINTS.tokenDetails}${symbol}`);
    }

    /**
     * Fetches journal entries.
     * @returns {Promise<Array>} A promise that resolves to a list of journal entries.
     */
    async function fetchJournalEntries() {
        return fetchData(API_ENDPOINTS.journal);
    }

    /**
     * Posts a new journal entry.
     * @param {Object} entryData - The data for the new journal entry (title, content, tags).
     * @returns {Promise<Object>} A promise that resolves to the new entry data.
     */
    async function postJournalEntry(entryData) {
        try {
            const response = await fetch(API_ENDPOINTS.journal, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(entryData)
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error("Error posting journal entry:", error);
            return null;
        }
    }

    /**
     * Fetches speculative analysis for a given symbol.
     * @param {string} symbol - The cryptocurrency symbol (e.g., BTC-USD).
     * @returns {Promise<Object>} A promise that resolves to the AI analysis.
     */
    async function fetchSpeculativeAnalysis(symbol) {
        return fetchData(`${API_ENDPOINTS.speculativeAnalysis}${symbol}`);
    }

    /**
     * Updates the Performance Metrics panel.
     * @param {Object} summary - The portfolio summary data.
     */
    function updatePerformanceMetrics(summary) {
        const kpiContent = document.getElementById('kpi-content');
        if (!summary || !kpiContent) return;

        const formatMetric = (value, decimals = 2) => (value ? value.toFixed(decimals) : 'N/A');
        const getColorClass = (value) => (value >= 0 ? 'text-positive' : 'text-negative');

        kpiContent.innerHTML = `
            <p><strong>Total Value:</strong> $${formatMetric(summary.current_portfolio_value)}</p>
            <p><strong>Sharpe Ratio:</strong> ${formatMetric(summary.sharpe_ratio, 4)}</p>
            <p><strong>Sortino Ratio:</strong> ${formatMetric(summary.sortino_ratio, 4)}</p>
            <p class="${getColorClass(summary.max_drawdown)}"><strong>Max Drawdown:</strong> ${formatMetric(summary.max_drawdown * 100)}%</p>
        `;
    }

    /**
     * Updates the Holdings panel.
     * @param {Object} summary - The portfolio summary data.
     */
    function updateHoldings(summary) {
        const holdingsContent = document.getElementById('holdings-content');
        if (!summary || !holdingsContent) return;

        const holdings = summary.holdings || {};
        if (Object.keys(holdings).length === 0) {
            holdingsContent.innerHTML = '<p>No current holdings.</p>';
            return;
        }

        let html = '<ul class="list-group list-group-flush">';
        for (const symbol in holdings) {
            const holding = holdings[symbol];
            const pnl = holding.current_value - (holding.amount * holding.avg_entry_price);
            const pnlPercent = (pnl / (holding.amount * holding.avg_entry_price)) * 100;
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-center" data-symbol="${symbol}">
                    <div>
                        <strong>${symbol}</strong><br>
                        <small>${holding.amount.toFixed(4)} @ ${holding.avg_entry_price.toFixed(2)}</small>
                    </div>
                    <span class="${pnl >= 0 ? 'text-positive' : 'text-negative'}">
                        ${pnl.toFixed(2)} (${pnlPercent.toFixed(2)}%)
                    </span>
                </li>`;
        }
        html += '</ul>';
        holdingsContent.innerHTML = html;

        // Add click listener to holdings list items
        const holdingsList = holdingsContent.querySelector('ul');
        if (holdingsList) {
            holdingsList.addEventListener('click', async (event) => {
                const listItem = event.target.closest('li[data-symbol]');
                if (listItem) {
                    const symbol = listItem.dataset.symbol;
                    const details = await fetchTokenDetails(symbol);
                    updateTokenDetails(details);
                    const analysis = await fetchSpeculativeAnalysis(symbol);
                    updateSpeculativeAnalysis(analysis);
                }
            });
        }
    }

    /**
     * Updates the Token Details panel.
     * @param {Object} details - The token details data.
     */
    function updateTokenDetails(details) {
        const tokenDetailsContent = document.getElementById('token-details-content');
        if (!details || !tokenDetailsContent) return;

        let html = `
            <p><strong>Symbol:</strong> ${details.symbol}</p>
            <p><strong>Type:</strong> ${details.type}</p>
            <p><strong>Current Price:</strong> ${details.current_price}</p>
            <h6>Metrics:</h6>
            <ul>
        `;
        for (const key in details.metrics) {
            html += `<li><strong>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong> ${details.metrics[key]}</li>`;
        }
        html += `</ul>`;
        tokenDetailsContent.innerHTML = html;
    }

    /**
     * Updates the Trading Journal panel.
     * @param {Array} entries - An array of journal entries.
     */
    function updateJournalPanel(entries) {
        const journalEntriesDiv = document.getElementById('journal-entries');
        if (!journalEntriesDiv) return;

        let entriesHtml = '';
        if (entries.length === 0) {
            entriesHtml += '<p class="text-muted">No journal entries yet.</p>';
        } else {
            entries.forEach(entry => {
                entriesHtml += `
                    <div class="card mb-2">
                        <div class="card-body">
                            <h6 class="card-title">${entry.title} <small class="text-muted float-end">${new Date(entry.timestamp).toLocaleString()}</small></h6>
                            <p class="card-text">${entry.content}</p>
                            ${entry.tags ? `<p class="card-text"><small class="text-muted">Tags: ${entry.tags}</small></p>` : ''}
                        </div>
                    </div>
                `;
            });
        }
        journalEntriesDiv.innerHTML = entriesHtml;
    }

    /**
     * Updates the AI Speculative Analysis panel.
     * @param {Object} analysis - The speculative analysis data.
     */
    function updateSpeculativeAnalysis(analysis) {
        const aiAnalysisContent = document.getElementById('ai-analysis-content');
        if (!analysis || !aiAnalysisContent) return;

        let html = `
            <h6>Short-Term Outlook (1-7 days):</h6>
            <p>${analysis.short_term_outlook || 'N/A'}</p>
            <h6>Medium-Term Outlook (1-3 months):</h6>
            <p>${analysis.medium_term_outlook || 'N/A'}</p>
            <h6>Bullish Factors:</h6>
            <ul>
        `;
        (analysis.bullish_factors || []).forEach(factor => {
            html += `<li>${factor}</li>`;
        });
        html += `
            </ul>
            <h6>Bearish Factors:</h6>
            <ul>
        `;
        (analysis.bearish_factors || []).forEach(factor => {
            html += `<li>${factor}</li>`;
        });
        html += `</ul>`;
        aiAnalysisContent.innerHTML = html;
    }

    /**
     * Updates the main portfolio chart.
     * @param {Object} summary - The portfolio summary data.
     */
    function updateMainChart(summary) {
        const ctx = document.getElementById('portfolio-chart').getContext('2d');
        if (!summary || !summary.equity_curve || !ctx) return;

        const labels = summary.equity_curve.map(d => new Date(d.date).toLocaleDateString());
        const data = summary.equity_curve.map(d => d.value);

        if (portfolioChart) {
            portfolioChart.data.labels = labels;
            portfolioChart.data.datasets[0].data = data;
            portfolioChart.update();
        } else {
            portfolioChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Portfolio Value',
                        data: data,
                        borderColor: '#0056b3',
                        backgroundColor: 'rgba(0, 86, 179, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    }
                }
            });
        }
    }

    /**
     * Updates the footer status.
     * @param {Object} status - The system status data.
     */
    function updateFooter(status) {
        const systemStatusEl = document.getElementById('system-status');
        const marketRegimeEl = document.getElementById('market-regime');
        if (!status || !systemStatusEl || !marketRegimeEl) return;

        systemStatusEl.textContent = status.status || 'Unknown';
        marketRegimeEl.textContent = status.regime || 'Unknown';
    }

    /**
     * Main function to update all dashboard components.
     */
    async function updateDashboard() {
        const summary = await fetchData(API_ENDPOINTS.portfolioSummary);
        const status = await fetchData(API_ENDPOINTS.status);
        const journalEntries = await fetchJournalEntries();

        updatePerformanceMetrics(summary);
        updateHoldings(summary);
        updateMainChart(summary);
        updateFooter(status);
        updateJournalPanel(journalEntries);
        // Call placeholder update functions for future panels
        updateAlphaStream();
        updateStrategyPlayground();
        updatePairsScanner();
        updatePortfolioOptimization();
        updateNarrativeExposure();
    }

    // --- Placeholder functions for future panels ---
    function updateAlphaStream() { document.getElementById('alpha-stream-content').innerHTML = '<p class="text-muted">Alpha Stream module not yet implemented.</p>'; }
    function updateStrategyPlayground() { document.getElementById('strategy-playground-content').innerHTML = '<p class="text-muted">Strategy Playground module not yet implemented.</p>'; }
    function updatePairsScanner() { document.getElementById('pairs-scanner-content').innerHTML = '<p class="text-muted">Pairs Scanner module not yet implemented.</p>'; }
    function updatePortfolioOptimization() { document.getElementById('portfolio-optimization-content').innerHTML = '<p class="text-muted">Portfolio Optimization module not yet implemented.</p>'; }
    function updateNarrativeExposure() { document.getElementById('narrative-exposure-content').innerHTML = '<p class="text-muted">Narrative Exposure module not yet implemented.</p>'; }

    // Initial load and set interval for periodic updates
    updateDashboard();
    setInterval(updateDashboard, 30000); // Refresh every 30 seconds

    // Event listener for journal form submission
    const journalForm = document.getElementById('journal-form');
    if (journalForm) {
        journalForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const title = document.getElementById('journal-title').value;
            const content = document.getElementById('journal-content').value;
            const tags = document.getElementById('journal-tags').value;

            const newEntry = await postJournalEntry({ title, content, tags });
            if (newEntry) {
                alert('Journal entry added successfully!');
                journalForm.reset(); // Clear the form
                updateJournalPanel(await fetchJournalEntries()); // Refresh journal entries
            } else {
                alert('Failed to add journal entry.');
            }
        });
    }
});