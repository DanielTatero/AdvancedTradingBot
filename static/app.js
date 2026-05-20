let analysisData = {}; // Objeto global para almacenar los análisis y abrirlos al hacer clic

document.addEventListener('DOMContentLoaded', () => {
    
    const loadPortfolio = async () => {
        document.getElementById('portfolio-loader').style.display = 'block';
        document.getElementById('portfolio-grid').style.display = 'none';
        
        try {
            const res = await fetch('/api/portfolio');
            const data = await res.json();
            
            if (data.market_gain && data.market_gain !== "N/A") {
                const gainDisplay = document.getElementById('market-gain-display');
                if (gainDisplay) gainDisplay.innerText = data.market_gain;
            }
            
            renderCards(data.portfolio || data, 'portfolio-grid', false);
        } catch (error) {
            console.error('Error fetching portfolio:', error);
            document.getElementById('portfolio-loader').innerText = 'Error al cargar los datos de la cartera.';
        }
    };

    const loadOpportunities = async () => {
        document.getElementById('opportunities-loader').style.display = 'block';
        document.getElementById('opportunities-grid').style.display = 'none';
        
        try {
            const res = await fetch('/api/opportunities');
            const data = await res.json();
            renderCards(data, 'opportunities-grid', true);
        } catch (error) {
            console.error('Error fetching opportunities:', error);
            document.getElementById('opportunities-loader').innerText = 'Error al cargar oportunidades del mercado.';
        }
    };

    const renderCards = (data, containerId, isClickable) => {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        
        if (data.length === 0) {
            container.innerHTML = '<p style="color: #9ca3af; grid-column: 1 / -1;">No hay datos disponibles o hubo un error.</p>';
        }

        data.forEach(item => {
            // Guardar texto de análisis globalmente
            analysisData[item.ticker] = item.analysis_text;

            const card = document.createElement('div');
            card.className = 'card';
            if (isClickable) {
                card.classList.add('clickable-card');
                card.onclick = () => showAnalysis(item.ticker);
            }
            
            // Format RSI color
            let rsiColor = '#f3f4f6';
            if (item.rsi !== "N/A") {
                if (item.rsi < 30) rsiColor = '#10b981'; // oversold (buy)
                else if (item.rsi > 70) rsiColor = '#ef4444'; // overbought (sell)
            }

            // Signals HTML
            let signalsHtml = '';
            if (item.signals.length > 0) {
                signalsHtml = '<div class="signals">';
                item.signals.forEach(sig => {
                    let typeClass = '';
                    if (sig.includes('Alcista') || sig.includes('Sobreventa') || sig.includes('Rebote')) typeClass = 'bullish';
                    else if (sig.includes('Bajista') || sig.includes('Sobrecompra') || sig.includes('Corrección')) typeClass = 'bearish';
                    
                    signalsHtml += `<div class="signal-badge ${typeClass}">• ${sig}</div>`;
                });
                signalsHtml += '</div>';
            } else {
                signalsHtml = '<div class="signals"><div class="signal-badge">• Sin señales de alerta fuertes</div></div>';
            }

            let targetHtml = '';
            if (item.entry_price !== undefined) {
                targetHtml = `
                    <div style="margin-bottom: 15px; padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.2);">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="font-size: 0.8rem; color: #9ca3af;">Entrada Sugerida</span>
                            <span style="font-size: 0.9rem; font-weight: 600; color: #10b981;">~$${item.entry_price}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="font-size: 0.8rem; color: #9ca3af;">Toma Ganancia</span>
                            <span style="font-size: 0.9rem; font-weight: 600; color: #3b82f6;">$${item.take_profit}</span>
                        </div>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="card-header">
                    <span class="ticker">${item.ticker}</span>
                    <span class="price">$${item.price}</span>
                </div>
                <div class="metrics">
                    <div class="metric">
                        <span class="metric-label">RSI (14)</span>
                        <span class="metric-value" style="color: ${rsiColor}">${item.rsi}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">MACD</span>
                        <span class="metric-value">${item.macd}</span>
                    </div>
                </div>
                ${targetHtml}
                ${signalsHtml}
            `;
            container.appendChild(card);
        });

        document.getElementById(containerId.replace('grid', 'loader')).style.display = 'none';
        container.style.display = 'grid';
    };

    // Initial load
    loadPortfolio();
    loadOpportunities();

    // Event listeners
    document.getElementById('refresh-portfolio').addEventListener('click', loadPortfolio);
    document.getElementById('refresh-opportunities').addEventListener('click', loadOpportunities);
});

// ---- Funciones Globales para UI ----

window.switchTab = function(tabId) {
    // Ocultar todas las solapas
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active-tab');
    });
    // Quitar active de los botones
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Mostrar la solapa seleccionada
    document.getElementById(tabId + '-tab').classList.add('active-tab');
    event.currentTarget.classList.add('active');
};

window.showAnalysis = function(ticker) {
    if(!analysisData[ticker]) return;
    const modal = document.getElementById('analysis-modal');
    document.getElementById('modal-title').innerText = `📊 Análisis de ${ticker}`;
    document.getElementById('modal-body').innerHTML = analysisData[ticker];
    modal.style.display = 'block';
};

window.closeModal = function() {
    document.getElementById('analysis-modal').style.display = 'none';
};

// Cerrar modal si se hace clic fuera de la ventana
window.onclick = function(event) {
    const modal = document.getElementById('analysis-modal');
    if (event.target == modal) {
        modal.style.display = "none";
    }
}
