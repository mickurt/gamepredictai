// --- AUTH LOGIC (Global to be available immediately) ---
window.switchAuth = function (mode) {
    console.log("Switching auth to:", mode);
    const tabs = document.querySelectorAll('.auth-tab');
    const signupForm = document.getElementById('signupForm');
    const loginForm = document.getElementById('loginForm');
    const lostPasswordForm = document.getElementById('lostPasswordForm');
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    const msg = document.getElementById('authMessage');

    // Remove active from all tabs
    tabs.forEach(t => t.classList.remove('active'));
    
    // Hide all forms
    if (signupForm) signupForm.style.display = 'none';
    if (loginForm) loginForm.style.display = 'none';
    if (lostPasswordForm) lostPasswordForm.style.display = 'none';
    if (resetPasswordForm) resetPasswordForm.style.display = 'none';
    if (msg) msg.textContent = '';

    if (mode === 'signup') {
        const tab = document.getElementById('tab-signup') || document.querySelector('.auth-tab[onclick*="signup"]');
        if (tab) tab.classList.add('active');
        if (signupForm) signupForm.style.display = 'flex';
    } else if (mode === 'login') {
        const tab = document.getElementById('tab-login') || document.querySelector('.auth-tab[onclick*="login"]');
        if (tab) tab.classList.add('active');
        if (loginForm) loginForm.style.display = 'flex';
    } else if (mode === 'lost_password') {
        if (lostPasswordForm) lostPasswordForm.style.display = 'flex';
    } else if (mode === 'reset_password') {
        if (resetPasswordForm) resetPasswordForm.style.display = 'flex';
    }
};

// --- API CONFIGURATION ---
const API_BASE = (window.location.hostname.includes('hf.space') || 
                  window.location.hostname === 'localhost' || 
                  window.location.hostname === '127.0.0.1') 
                  ? '' 
                  : 'https://mickurt-gaming-ai-predictor.hf.space';

document.addEventListener('DOMContentLoaded', async () => {
    
    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get('reset_token');
    if (resetToken) {
        // CLEAN VIEW: Hide the rest of the landing page for reset
        const hero = document.getElementById('landing-hero-content');
        const features = document.getElementById('featuresSection');
        if (hero) hero.style.display = 'none';
        if (features) features.style.display = 'none';
        
        document.getElementById('landingPage').classList.add('reset-mode');
        switchAuth('reset_password');
    }

    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('signupEmail').value.toLowerCase().trim();
            const password = document.getElementById('signupPassword').value;
            const organization = document.getElementById('signupOrg').value;
            const msg = document.getElementById('authMessage');
            msg.textContent = 'Submitting request...';
            msg.style.color = '#fff';

            try {
                const res = await fetch(`${API_BASE}/api/signup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, organization })
                });
                const data = await res.json();
                if (res.ok) {
                    msg.textContent = data.message;
                    msg.style.color = '#00ff88';
                    e.target.reset();
                } else {
                    msg.textContent = data.message;
                    msg.style.color = '#ff4444';
                }
            } catch (err) {
                msg.textContent = 'Error connecting to server. Please try again.';
                msg.style.color = '#ff4444';
            }
        });
    }

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value.toLowerCase().trim();
            const password = document.getElementById('loginPassword').value;
            const msg = document.getElementById('authMessage');
            msg.textContent = 'Logging in...';
            msg.style.color = '#fff';

            try {
                const res = await fetch(`${API_BASE}/api/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                const data = await res.json();
                if (res.ok) {
                    window.currentUserId = data.user_id;
                    localStorage.setItem('gamepredict_user_id', data.user_id);
                    document.getElementById('landingPage').style.display = 'none';
                    document.getElementById('dashboardApp').style.display = 'flex';
                } else {
                    msg.textContent = data.message;
                    msg.style.color = '#ff4444';
                }
            } catch (err) {
                msg.textContent = 'Error connecting to server. Please try again.';
                msg.style.color = '#ff4444';
            }
        });
    }

    const lostPasswordForm = document.getElementById('lostPasswordForm');
    if (lostPasswordForm) {
        lostPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('lostPasswordEmail').value.toLowerCase().trim();
            const msg = document.getElementById('authMessage');
            msg.textContent = 'Sending reset link...';
            msg.style.color = '#fff';

            try {
                const res = await fetch(`${API_BASE}/api/lost_password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                const data = await res.json();
                if (res.ok) {
                    msg.textContent = data.message;
                    msg.style.color = '#00ff88';
                    e.target.reset();
                } else {
                    msg.textContent = data.message;
                    msg.style.color = '#ff4444';
                }
            } catch (err) {
                msg.textContent = 'Error connecting to server. Please try again.';
                msg.style.color = '#ff4444';
            }
        });
    }

    const resetPasswordForm = document.getElementById('resetPasswordForm');
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const newPassword = document.getElementById('newPassword').value;
            const confirmNewPassword = document.getElementById('confirmNewPassword').value;
            const msg = document.getElementById('authMessage');

            if (newPassword !== confirmNewPassword) {
                msg.textContent = 'Passwords do not match.';
                msg.style.color = '#ff4444';
                return;
            }

            msg.textContent = 'Resetting password...';
            msg.style.color = '#fff';

            try {
                const res = await fetch(`${API_BASE}/api/reset_password`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: resetToken, new_password: newPassword })
                });
                const data = await res.json();
                if (res.ok) {
                    msg.textContent = data.message;
                    msg.style.color = '#00ff88';
                    e.target.reset();
                    setTimeout(() => {
                        window.location.href = window.location.pathname; // remove token and switch to login
                    }, 2000);
                } else {
                    msg.textContent = data.message;
                    msg.style.color = '#ff4444';
                }
            } catch (err) {
                msg.textContent = 'Error connecting to server. Please try again.';
                msg.style.color = '#ff4444';
            }
        });
    }

    const analyzeSentimentBtn = document.getElementById('analyzeSentimentBtn');
    const gameName = document.getElementById('gameName');
    const sentimentResult = document.getElementById('sentimentResult');
    let currentSentimentScore = null;
    let currentBuzzReason = null;

    // --- ANALYZE SENTIMENT (IA) ---
    async function runBuzzAnalysis() {
        const name = gameName.value.trim();
        const similars = document.getElementById('similarGames').value || "";
        const apiKey = document.getElementById('apiKey').value;

        console.log("Buzz Analysis Started. Name:", name);

        if (!name) return; // Silent exit if no name

        if (analyzeSentimentBtn) {
            analyzeSentimentBtn.textContent = "Searching Buzz...";
            analyzeSentimentBtn.disabled = true;
        }

        try {
            const formData = new FormData();
            formData.append('game_name', name);
            formData.append('similar_games', similars);
            formData.append('api_key', apiKey);

            const res = await fetch(`${API_BASE}/api/analyze_sentiment`, { method: 'POST', body: formData });

            if (!res.ok) {
                const err = await res.text();
                throw new Error(res.status + " " + err);
            }

            const data = await res.json();

            if (data.score) {
                currentSentimentScore = data.score;
                currentBuzzReason = data.reason;
                const buzzBadge = document.getElementById('sentimentResult');
                if (buzzBadge) {
                    buzzBadge.style.display = 'inline-block';
                    document.getElementById('buzzScore').textContent = data.score;
                    document.getElementById('buzzText').textContent = data.reason ? `(${data.reason})` : "";
                    console.log("✅ Buzz Analysis UI Updated:", data.score);
                }

                // Auto-update inputs (only if empty or <= 0)
                const sIn = document.getElementById('sentiment');
                if (sIn && (!sIn.value || parseFloat(sIn.value) <= 0)) {
                    if (data.sentiment_percent) {
                        sIn.value = data.sentiment_percent;
                    } else {
                        if (data.score >= 8) sIn.value = 90;
                        else if (data.score <= 4) sIn.value = 40;
                        else sIn.value = 75;
                    }
                    sIn.style.borderColor = "#00ff88";
                    setTimeout(() => sIn.style.borderColor = "", 2000);
                }

                if (data.previous_sales) {
                    const ps = document.getElementById('prevSales');
                    if (ps && (!ps.value || parseFloat(ps.value) <= 0)) { ps.value = data.previous_sales; ps.style.borderColor = "#00ff88"; setTimeout(() => ps.style.borderColor = "", 2000); }
                }
                if (data.previous_sentiment) {
                    const psnt = document.getElementById('prevSentiment');
                    if (psnt && (!psnt.value || parseFloat(psnt.value) <= 0)) { psnt.value = data.previous_sentiment; psnt.style.borderColor = "#00ff88"; setTimeout(() => psnt.style.borderColor = "", 2000); }
                }
                if (data.previous_buzz) {
                    const pb = document.getElementById('prevBuzz');
                    if (pb && (!pb.value || parseFloat(pb.value) <= 0)) { pb.value = data.previous_buzz; pb.style.borderColor = "#00ff88"; setTimeout(() => pb.style.borderColor = "", 2000); }
                }
                if (data.similar_games) {
                    const simI = document.getElementById('similarGames');
                    if (simI && !simI.value.trim()) { simI.value = data.similar_games; simI.style.borderColor = "#00ff88"; setTimeout(() => simI.style.borderColor = "", 2000); }
                }
            }
        } catch (e) {
            console.error("Buzz Analysis Error:", e);
        } finally {
            if (analyzeSentimentBtn) {
                analyzeSentimentBtn.textContent = "🧐 Analyze Buzz (IA)";
                analyzeSentimentBtn.disabled = false;
            }
        }
    }

    // --- INIT ---
    const genreSelect = document.getElementById('genreSelect');
    const form = document.getElementById('predictionForm');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const previewImage = document.getElementById('previewImage');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultsArea = document.getElementById('resultsArea');
    const loader = document.getElementById('loader');

    // Global chart instances
    let profitChartInstance = null;
    let salesChartInstance = null;
    let compSalesChartInstance = null;
    let monteCarloChartInstance = null;
    let marketingChartInstance = null;
    let pricingChartInstance = null;

    // --- RESET / NEW SEARCH ---
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            // 1. Reset Form
            form.reset();
            
            // 2. Clear AI persistence
            currentSentimentScore = null;
            currentBuzzReason = null;
            
            // 3. Clear UI specific elements
            if (previewImage) {
                previewImage.src = "";
                previewImage.style.display = 'none';
            }
            if (dropZone) dropZone.querySelector('p').style.display = 'block';
            if (analyzeBtn) analyzeBtn.style.display = 'none';
            
            const sr = document.getElementById('sentimentResult');
            if (sr) sr.style.display = 'none';
            
            const ac = document.getElementById('aiContext');
            if (ac) ac.innerHTML = "Perform a prediction to see AI insights.";
            
            // 4. Reset Results Area
            resultsArea.style.opacity = '0.5';
            resultsArea.style.pointerEvents = 'none';
            
            // 5. Destroy Charts
            if (profitChartInstance) { profitChartInstance.destroy(); profitChartInstance = null; }
            if (salesChartInstance) { salesChartInstance.destroy(); salesChartInstance = null; }
            if (compSalesChartInstance) { compSalesChartInstance.destroy(); compSalesChartInstance = null; }
            if (monteCarloChartInstance) { monteCarloChartInstance.destroy(); monteCarloChartInstance = null; }
            if (marketingChartInstance) { marketingChartInstance.destroy(); marketingChartInstance = null; }
            if (pricingChartInstance) { pricingChartInstance.destroy(); pricingChartInstance = null; }
            
            // 6. Reset values in cards
            const mp = document.getElementById('maxProfit');
            if (mp) mp.textContent = "$ ---";
            const bi = document.getElementById('benchmarkInfo');
            if (bi) bi.innerHTML = '--- <span style="font-size:0.8rem">copies</span>';
            
            // 7. Clear tables
            const mb = document.getElementById('marketingBody');
            if (mb) mb.innerHTML = '';
            const db = document.getElementById('dynamicBody');
            if (db) db.innerHTML = '';
            const cb = document.getElementById('comparablesBody');
            if (cb) cb.innerHTML = '';
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) sidebar.scrollTo({ top: 0, behavior: 'smooth' });
            
            console.log("🔄 Search reset successfully.");
        });
    }

    // --- DRAG & DROP ---
    let selectedFile = null;
    let currentPredictionData = null; // Store latest result

    // Load Genres
    try {
        const res = await fetch(`${API_BASE}/api/genres`);
        const genres = await res.json();
        genreSelect.innerHTML = '';
        Object.keys(genres).forEach(g => {
            const opt = document.createElement('option');
            opt.value = g;
            opt.textContent = g;
            genreSelect.appendChild(opt);
        });
        // Set default
        genreSelect.value = "Adventure";
    } catch (e) {
        console.error("Failed to load genres", e);
    }

    // --- INTERACTION: SWITCH CHARTS ---
    // (Moved to renderResults for better data binding)

    // --- DRAG & DROP ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary)';
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--glass-border)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--glass-border)';
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
    });

    function handleFile(file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            previewImage.style.display = 'block';
            dropZone.querySelector('p').style.display = 'none';
            analyzeBtn.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    // --- ANALYZE IMAGE (GEMINI) ---
    analyzeBtn.addEventListener('click', async () => {
        const apiKey = document.getElementById('apiKey').value;
        if (!apiKey) {
            alert("Please enter a Gemini API Key first.");
            return;
        }

        analyzeBtn.textContent = "Analyzing...";
        analyzeBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('api_key', apiKey);

        try {
            const res = await fetch(`${API_BASE}/api/analyze_image`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (data.similar_games && data.similar_games.length > 0) {
                document.getElementById('similarGames').value = data.similar_games.join(', ');
                alert(`Found matches: ${data.similar_games.join(', ')}`);
            } else {
                alert("No specific matches found. Try another image.");
            }
        } catch (e) {
            alert("Analysis failed. Check console.");
            console.error(e);
        } finally {
            analyzeBtn.textContent = "✨ Analyze with Gemini";
            analyzeBtn.disabled = false;
        }
    });

    // --- PREDICT ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // UI Loading
        resultsArea.style.opacity = '0.1';
        loader.style.display = 'block';

        // --- AUTO BUZZ ANALYSIS if name provided ---
        const gName = document.getElementById('gameName').value.trim();
        if (gName) {
            await runBuzzAnalysis();
        }

        const formData = new FormData();
        formData.append('genre', genreSelect.value);
        formData.append('budget', document.getElementById('budget').value || "0");
        formData.append('wishlists', document.getElementById('wishlists').value || "");
        formData.append('sentiment', document.getElementById('sentiment').value || "0");
        formData.append('month', document.getElementById('month').value || "10");
        formData.append('langs', document.getElementById('langs').value || "5");
        formData.append('similar_games', document.getElementById('similarGames').value || "");
        formData.append('game_name', document.getElementById('gameName').value || "");
        formData.append('fixed_price', document.getElementById('fixedPrice').value || "");
        formData.append('previous_sales', document.getElementById('prevSales').value || "");
        formData.append('previous_sentiment', document.getElementById('prevSentiment').value || "");
        formData.append('previous_buzz', document.getElementById('prevBuzz').value || "");
        formData.append('num_dlcs', document.getElementById('numDlcs').value || "0");
        formData.append('dlc_price', document.getElementById('dlcPrice').value || "0");
        if (currentSentimentScore) formData.append('sentiment_ia_score', currentSentimentScore);
        formData.append('user_id', window.currentUserId || "Guest");

        try {
            const res = await fetch(`${API_BASE}/api/predict`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errDetail = await res.json();
                throw new Error(JSON.stringify(errDetail, null, 2));
            }

            const data = await res.json();
            currentPredictionData = data; // Save for interaction
            renderResults(data);
        } catch (error) {
            console.error(error);
            alert("Prediction Error:\n" + error.message);
        } finally {
            resultsArea.style.opacity = '1';
            resultsArea.style.pointerEvents = 'all';
            loader.style.display = 'none';
        }
    });

    function renderResults(data) {
        // document.getElementById('optPrice').textContent = `$${data.best_price.toFixed(2)}`;
        // Format big numbers
        document.getElementById('maxProfit').textContent = `$${Math.floor(data.max_profit).toLocaleString()}`;
        
        // --- SHOW BUZZ SCORE ---
        let displayScore = data.sentiment_ia_score || currentSentimentScore;
        const displayReason = data.reason || currentBuzzReason;
        const buzzBadge = document.getElementById('sentimentResult');

        // Fallback: If no score from AI, we might have it in the result if engine calculated it
        if (!displayScore && data.sentiment_ia_score === 0) displayScore = 0.1; // Ensure 0 is showable

        if (displayScore && buzzBadge) {
            buzzBadge.style.display = 'inline-block';
            const scoreEl = document.getElementById('buzzScore');
            const textEl = document.getElementById('buzzText');
            if (scoreEl) scoreEl.textContent = displayScore;
            if (textEl) textEl.textContent = displayReason ? `(${displayReason})` : ""; 
            console.log("✅ Rendering Buzz Score:", displayScore);
        } else if (buzzBadge) {
            // Keep it hidden ONLY if truly no score
            buzzBadge.style.display = 'none';
        }

        // --- UPDATE WISHLISTS FIELD IF ESTIMATED ---
        const wishlistInput = document.getElementById('wishlists');
        if (data.wishlists && (!wishlistInput.value || wishlistInput.value == "0")) {
            wishlistInput.value = data.wishlists;
            wishlistInput.style.borderColor = "#00ff88";
            setTimeout(() => wishlistInput.style.borderColor = "", 2000);
        }
        
        // Update Benchmark Card to show Volume
        const salesStr = data.est_total_sales ? data.est_total_sales.toLocaleString() : "---";
        document.getElementById('benchmarkInfo').innerHTML = `
            <div style="font-size:1.4rem; color:#fff">${salesStr} <span style="font-size:0.8rem">copies</span></div>
        `;
        // Find parent card and update title
        const salesCard = document.getElementById('benchmarkInfo').parentElement;
        salesCard.querySelector('h3').textContent = "Est. Total Sales";

        // Reset interaction styles
        salesCard.style.cursor = "default";
        salesCard.onmouseover = null;
        salesCard.onmouseout = null;
        salesCard.onclick = null;
        salesCard.style.transform = "none";

        const profitCard = document.getElementById('maxProfit').parentElement;
        profitCard.style.cursor = "default";
        profitCard.onclick = null;

        // RENDER BOTH CHARTS
        renderBreakEvenChart(data);
        renderEvolutionChart(data);
        renderComparables(data.comparable_games);
        if (data.monte_carlo) renderMonteCarloChart(data.monte_carlo, data.est_total_sales);
        if (data.dynamic_pricing) renderDynamicPricing(data.dynamic_pricing);
        if (data.marketing_efficiency) renderMarketingEfficiency(data.marketing_efficiency);
        if (data.global_risk) renderGlobalRisk(data.global_risk);
        if (data.greenlight) renderGreenlightScore(data.greenlight);

        // AI Context
        let contextText = data.context_review || `Based on your parameters, AI classifies this as a <b>${data.segment_label}</b> project.`;
        
        if (data.sentiment_ia_score) {
            contextText = `<b>AI Buzz detected:</b> ${data.sentiment_ia_score}/10. <br>` + contextText;
        }

        if (data.used_similars && data.used_similars.length > 0) {
            contextText += `<br><br><b>Visual Benchmark:</b> Analysis based on similar titles like: <i>${data.used_similars.join(', ')}</i>.`;
        }
        if (data.game_specific_match) {
            contextText += `<br><br><b>🎯 Exact Match:</b> Found data for "<i>${data.game_specific_match}</i>". Using specific metrics.`;
        }
        document.getElementById('aiContext').innerHTML = contextText;

    }

    function renderMarketingEfficiency(marketingData) {
        if (!marketingData || marketingData.length === 0) return;

        const tableBody = document.getElementById('marketingBody');
        const tableElement = document.getElementById('marketingTable');
        tableBody.innerHTML = '';
        tableElement.style.display = 'table';

        const labels = [];
        const rois = [];

        marketingData.forEach(m => {
            labels.push('$' + (m.budget / 1000000) + 'M');
            rois.push(m.roi);

            const row = document.createElement('tr');

            const thPrice = document.createElement('td');
            thPrice.textContent = '$' + (m.budget / 1000000) + 'M';
            thPrice.style.fontWeight = 'bold';
            row.appendChild(thPrice);

            const tdLift = document.createElement('td');
            tdLift.textContent = '+' + m.lift_percentage + '%';
            if (m.lift_percentage > 50) tdLift.style.color = '#00ff88';
            else if (m.lift_percentage > 20) tdLift.style.color = '#f39c12';
            row.appendChild(tdLift);

            const tdRoi = document.createElement('td');
            tdRoi.textContent = m.roi + '%';
            if (m.roi > 0) tdRoi.style.color = '#00ff88';
            else tdRoi.style.color = '#ff4444';
            row.appendChild(tdRoi);

            tableBody.appendChild(row);
        });

        // Chart
        const ctx = document.getElementById('marketingChart').getContext('2d');
        if (marketingChartInstance) marketingChartInstance.destroy();

        marketingChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Expected ROI (%)',
                    data: rois,
                    borderColor: '#9b59b6',
                    backgroundColor: 'rgba(155, 89, 182, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: 'white' } },
                    title: {
                        display: true,
                        text: 'Marketing Budgets & Diminishing Returns',
                        color: 'rgba(255,255,255,0.7)'
                    }
                },
                scales: {
                    x: { ticks: { color: 'rgba(255,255,255,0.7)' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                    y: { ticks: { color: 'rgba(255,255,255,0.7)' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                }
            }
        });
    }

    function renderGlobalRisk(risk) {
        if (!risk) return;
        document.getElementById('riskOverall').textContent = risk.overall + "/10";
        document.getElementById('riskMarket').textContent = risk.market_risk + "/10";
        document.getElementById('riskBudget').textContent = risk.budget_risk + "/10";
        document.getElementById('riskGenre').textContent = risk.genre_risk + "/10";
        if (document.getElementById('riskBuzz')) {
            document.getElementById('riskBuzz').textContent = (risk.buzz_risk !== undefined ? risk.buzz_risk : "---") + "/10";
        }

        const riskCardFranchise = document.getElementById('riskCardFranchise');
        if (riskCardFranchise) {
            if (risk.franchise_risk !== undefined) {
                riskCardFranchise.style.display = 'block';
                document.getElementById('riskFranchise').textContent = risk.franchise_risk + "/10";
            } else {
                riskCardFranchise.style.display = 'none';
            }
        }

        const rCardOverall = document.getElementById('riskCardOverall');
        const rTitleOverall = document.getElementById('riskOverallTitle');
        if (risk.overall >= 7.5) {
            rCardOverall.style.borderLeft = "4px solid #ff4444";
            rCardOverall.style.background = "rgba(255, 68, 68, 0.05)";
            rTitleOverall.style.color = "#ff4444";
        } else if (risk.overall >= 4.5) {
            rCardOverall.style.borderLeft = "4px solid #f39c12";
            rCardOverall.style.background = "rgba(243, 156, 18, 0.05)";
            rTitleOverall.style.color = "#f39c12";
        } else {
            rCardOverall.style.borderLeft = "4px solid #00ff88";
            rCardOverall.style.background = "rgba(0, 255, 136, 0.05)";
            rTitleOverall.style.color = "#00ff88";
        }
    }

    function renderGreenlightScore(gl) {
        if (!gl) return;

        const card = document.getElementById('greenlightCard');
        const scoreText = document.getElementById('greenlightScoreText');
        const recText = document.getElementById('greenlightRecText');

        scoreText.innerHTML = `${gl.score}<span style="font-size: 1.5rem; opacity: 0.5;">/10</span>`;
        recText.textContent = gl.recommendation;

        if (gl.score >= 7.5) {
            card.style.borderLeft = "4px solid #00ff88";
            card.style.background = "rgba(0, 255, 136, 0.05)";
            recText.style.color = "#00ff88";
        } else if (gl.score >= 4.5) {
            card.style.borderLeft = "4px solid #f39c12";
            card.style.background = "rgba(243, 156, 18, 0.05)";
            recText.style.color = "#f39c12";
        } else {
            card.style.borderLeft = "4px solid #ff4444";
            card.style.background = "rgba(255, 68, 68, 0.05)";
            recText.style.color = "#ff4444";
        }
    }

    function renderBreakEvenChart(data) {
        const ctx = document.getElementById('profitSalesChart').getContext('2d');
        if (profitChartInstance) profitChartInstance.destroy();

        // Prepare datasets
        const datasets = [
            {
                label: 'Cumulative Net Profit ($)',
                data: data.breakeven_profits,
                borderColor: '#00d2ff',
                backgroundColor: 'rgba(0, 210, 255, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 0
            },
            {
                label: 'Break-even Point',
                data: data.breakeven_sales_steps.map(() => 0),
                borderColor: 'rgba(255, 255, 255, 0.3)',
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            }
        ];

        // Add year markers as points
        const milestones = data.year_milestones.map(m => ({
            x: m.cumulative_sales,
            y: m.cumulative_profit,
            label: m.year
        }));

        profitChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.breakeven_sales_steps,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: (items) => {
                                const sales = parseFloat(items[0].label);
                                return `Sales: ${Math.round(sales).toLocaleString()} units`;
                            }
                        }
                    },
                    annotation: {
                        // We could use Chartjs annotation plugin, but let's stick to standard for simplicity
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#928DAB',
                            callback: function (value) {
                                if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                                if (value >= 1000) return (value / 1000).toFixed(0) + 'k';
                                return value;
                            }
                        },
                        title: { display: true, text: 'Total Sales (Copies)', color: '#928DAB' }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#928DAB',
                            callback: function (value) { return '$' + value.toLocaleString(); }
                        },
                        title: { display: true, text: 'Cumulative Profit ($)', color: '#928DAB' }
                    }
                }
            }
        });
    }

    function renderEvolutionChart(data) {
        // Ensure element exists
        const canvas = document.getElementById('salesChart');
        if (!canvas) {
            console.error("Canvas #salesChart not found!");
            return;
        }

        // Debug Data
        console.log("📊 Evolution Check:", {
            years: data.evolution_years,
            sales: data.evolution_sales,
            revenue: data.evolution_revenue ? "YES" : "NO",
            profit: data.evolution_profit ? "YES" : "NO"
        });

        if (!data.evolution_years || !data.evolution_sales || data.evolution_sales.length === 0) {
            console.warn("No evolution data to render.");
            return;
        }

        const ctx = canvas.getContext('2d');
        if (salesChartInstance) salesChartInstance.destroy();

        salesChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.evolution_years,
                datasets: [
                    {
                        label: 'Annual Sales Volume (Copies)',
                        data: data.evolution_sales,
                        backgroundColor: 'rgba(0, 255, 136, 0.6)',
                        borderColor: '#00ff88',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#928DAB' }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#928DAB',
                            callback: function (value) { return value.toLocaleString(); }
                        }
                    }
                }
            }
        });

        // --- NEW: Financial Table Evolution ---
        const tableBody = document.getElementById('evolutionBody');
        const tableElement = document.getElementById('evolutionTable');
        
        if (tableBody && tableElement && data.evolution_revenue && data.evolution_profit) {
            tableBody.innerHTML = '';
            tableElement.style.display = 'table';
            
            data.evolution_years.forEach((year, i) => {
                const sales = data.evolution_sales[i] || 0;
                const revenue = data.evolution_revenue[i] || 0;
                const annualProfit = data.evolution_profit_annual ? data.evolution_profit_annual[i] : (data.evolution_revenue[i] || 0);
                const cumProfit = data.evolution_profit[i] || 0;
                
                const row = document.createElement('tr');
                row.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
                
                row.innerHTML = `
                    <td style="font-weight:600; color:var(--primary); padding: 12px;">${year}</td>
                    <td style="padding: 12px; font-weight: 500;">${sales.toLocaleString()} <span style="font-size:0.7rem; opacity:0.5;">units</span></td>
                    <td style="padding: 12px; color:#00d2ff; font-weight:600;">$${Math.round(revenue).toLocaleString()}</td>
                    <td style="padding: 12px; color:${annualProfit >= 0 ? '#00ff88' : '#ff4444'}; font-weight:600;">
                        $${Math.round(annualProfit).toLocaleString()}
                        ${annualProfit < 0 ? '<span style="font-size:0.6rem; opacity:0.6; display:block;">(Loss)</span>' : ''}
                    </td>
                    <td style="padding: 12px; color:${cumProfit >= 0 ? '#00ff88' : '#ff4444'}; font-weight:700;">
                        $${Math.round(cumProfit).toLocaleString()}
                        ${cumProfit < 0 ? '<span style="font-size:0.7rem; font-weight:400; display:block; opacity:0.6;">(Investment Phase)</span>' : ''}
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }
    }

    function renderComparables(comparables) {
        const tbody = document.getElementById('comparablesBody');
        const emptyMsg = document.getElementById('comparablesEmpty');
        const table = document.getElementById('comparablesTable');

        tbody.innerHTML = '';

        if (!comparables || comparables.length === 0) {
            emptyMsg.style.display = 'block';
            table.style.display = 'none';
            return;
        }

        emptyMsg.style.display = 'none';
        table.style.display = 'table';

        comparables.forEach((comp, index) => {
            const tr = document.createElement('tr');
            let budgetStr = '---';
            if (comp.budget > 0) {
                budgetStr = comp.budget >= 1000000 ? (comp.budget / 1000000).toFixed(1) + 'M' : (comp.budget / 1000).toFixed(0) + 'k';
            }

            let salesStr = '---';
            if (comp.sales > 0) {
                salesStr = comp.sales >= 1000000 ? (comp.sales / 1000000).toFixed(1) + 'M' : (comp.sales / 1000).toFixed(0) + 'k';
            }

            tr.innerHTML = `
                <td><strong>${comp.title}</strong></td>
                <td>${comp.type}</td>
                <td>$${budgetStr}</td>
                <td>$${comp.price > 0 ? comp.price.toFixed(2) : 'Free'}</td>
                <td>${comp.metacritic > 0 ? comp.metacritic.toFixed(0) : '---'}</td>
                <td>${salesStr}</td>
                <td><span class="sim-score">${comp.similarity}%</span></td>
                <td><button type="button" class="btn-outline view-curve-btn" data-index="${index}">View Curve</button></td>
            `;
            tbody.appendChild(tr);
        });

        // Add listeners to buttons
        document.querySelectorAll('.view-curve-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = e.target.getAttribute('data-index');
                const game = comparables[idx];
                showComparableCurve(game);
            });
        });
    }

    function showComparableCurve(game) {
        document.getElementById('compModalTitle').textContent = `Sales Curve: ${game.title}`;
        document.getElementById('comparableModal').style.display = 'flex';

        const canvas = document.getElementById('compSalesChart');
        const ctx = canvas.getContext('2d');
        if (compSalesChartInstance) compSalesChartInstance.destroy();

        compSalesChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: game.evolution_years,
                datasets: [
                    {
                        label: 'Annual Sales Volume (Copies)',
                        data: game.evolution_sales,
                        backgroundColor: 'rgba(0, 210, 255, 0.6)',
                        borderColor: '#00d2ff',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#928DAB' }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#928DAB',
                            callback: function (value) { return value.toLocaleString(); }
                        }
                    }
                }
            }
        });
    }

    function renderMonteCarloChart(mcData, estTotalSales) {
        document.getElementById('p10Sales').textContent = (mcData.p10 >= 1000000) ? (mcData.p10 / 1000000).toFixed(2) + 'M' : Math.floor(mcData.p10).toLocaleString();
        document.getElementById('p50Sales').textContent = (mcData.p50 >= 1000000) ? (mcData.p50 / 1000000).toFixed(2) + 'M' : Math.floor(mcData.p50).toLocaleString();
        document.getElementById('p90Sales').textContent = (mcData.p90 >= 1000000) ? (mcData.p90 / 1000000).toFixed(2) + 'M' : Math.floor(mcData.p90).toLocaleString();

        const canvas = document.getElementById('monteCarloChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (monteCarloChartInstance) monteCarloChartInstance.destroy();

        // format labels for bins
        const labels = mcData.histogram_bins.map(b => {
            if (b >= 1000000) return (b / 1000000).toFixed(1) + 'M';
            if (b >= 1000) return (b / 1000).toFixed(0) + 'k';
            return b.toFixed(0);
        });

        monteCarloChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Probability Distribution',
                    data: mcData.histogram_data,
                    backgroundColor: 'rgba(243, 156, 18, 0.2)',
                    borderColor: '#f39c12',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false } // simpler without a tooltip for a pure density chart
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#928DAB', maxRotation: 45, minRotation: 0 }
                    },
                    y: {
                        display: false, // hide the exact count to emphasize distribution curve shape
                        grid: { display: false }
                    }
                }
            },
            plugins: [{
                id: 'estimatedSalesLine',
                afterDraw: (chart) => {
                    if (!estTotalSales) return;

                    const ctx = chart.ctx;
                    const xAxis = chart.scales.x;
                    const yAxis = chart.scales.y;

                    const bins = mcData.histogram_bins;

                    let leftIdx = 0;
                    while (leftIdx < bins.length - 1 && bins[leftIdx + 1] <= estTotalSales) {
                        leftIdx++;
                    }

                    let binWidth = 0;
                    if (leftIdx < bins.length - 1) {
                        binWidth = bins[leftIdx + 1] - bins[leftIdx];
                    }

                    let fraction = 0;
                    if (binWidth > 0 && estTotalSales > bins[leftIdx]) {
                        fraction = (estTotalSales - bins[leftIdx]) / binWidth;
                    }

                    const meta = chart.getDatasetMeta(0);
                    let xPixel = xAxis.left; // fallback
                    if (meta.data && meta.data.length > 0) {
                        if (leftIdx < bins.length - 1 && meta.data[leftIdx] && meta.data[leftIdx + 1]) {
                            const p1 = meta.data[leftIdx].x;
                            const p2 = meta.data[leftIdx + 1].x;
                            xPixel = p1 + fraction * (p2 - p1);
                        } else if (meta.data[leftIdx]) {
                            xPixel = meta.data[leftIdx].x;
                        } else {
                            // if entirely out of bounds on right
                            xPixel = xAxis.right;
                        }
                    }

                    // Keep inside bounds conceptually, although the sales could be off-chart
                    if (xPixel < xAxis.left) xPixel = xAxis.left;
                    if (xPixel > xAxis.right) xPixel = xAxis.right;

                    ctx.save();
                    ctx.beginPath();
                    ctx.moveTo(xPixel, yAxis.top);
                    ctx.lineTo(xPixel, yAxis.bottom);
                    ctx.lineWidth = 2;
                    ctx.strokeStyle = '#00ff88';
                    ctx.setLineDash([5, 5]);
                    ctx.stroke();

                    // Label Background and Text
                    let text = 'Est. Sales';
                    let textWidth = ctx.measureText(text).width;

                    let textX = xPixel;
                    if (textX < xAxis.left + 35) textX = xAxis.left + 35;
                    if (textX > xAxis.right - 35) textX = xAxis.right - 35;

                    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    ctx.fillRect(textX - 35, yAxis.top, 70, 24);

                    ctx.fillStyle = '#00ff88';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.font = 'bold 12px sans-serif';
                    ctx.fillText(text, textX, yAxis.top + 12);

                    ctx.restore();
                }
            }]
        });
    }

    function renderDynamicPricing(pricingData) {
        const tbody = document.getElementById('pricingBody');
        const table = document.getElementById('pricingTable');

        tbody.innerHTML = '';
        table.style.display = 'table';

        const canvas = document.getElementById('pricingChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (pricingChartInstance) pricingChartInstance.destroy();

        if (!pricingData || pricingData.length === 0) {
            table.style.display = 'none';
            return;
        }

        // Find max profit for highlighting the "optimal" row among these points
        let maxProfit = -Infinity;
        pricingData.forEach(p => {
            if (p.profit > maxProfit) maxProfit = p.profit;
        });

        pricingData.forEach(pData => {
            const tr = document.createElement('tr');

            const isOptimal = (pData.profit === maxProfit);
            let optBadge = '';

            if (isOptimal) {
                tr.style.backgroundColor = 'rgba(0, 255, 136, 0.1)';
                optBadge = '<span style="font-size: 0.70rem; background: #00ff88; color: black; padding: 2px 6px; border-radius: 4px; margin-left:8px; vertical-align:middle;">Optimal</span>';
            }

            tr.innerHTML = `
                <td style="color:var(--primary); font-weight: bold; font-size: 1.1rem;">$${pData.price}${optBadge}</td>
                <td>${pData.sales.toLocaleString()} copies</td>
                <td>$${Math.floor(pData.revenue).toLocaleString()}</td>
                <td style="color: ${pData.profit > 0 ? '#00ff88' : '#ff4444'}">$${Math.floor(pData.profit).toLocaleString()}</td>
            `;
            tbody.appendChild(tr);
        });

        // Render Line Chart
        const labels = pricingData.map(p => '$' + p.price);
        const revenues = pricingData.map(p => Math.floor(p.revenue));

        // Highlight optimal point strictly on the chart
        const pointColors = pricingData.map(p => (p.profit === maxProfit) ? '#00ff88' : '#00d2ff');
        const pointRadii = pricingData.map(p => (p.profit === maxProfit) ? 8 : 4);

        pricingChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Expected Revenue',
                    data: revenues,
                    backgroundColor: 'rgba(0, 210, 255, 0.1)',
                    borderColor: '#00d2ff',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: pointColors,
                    pointBorderColor: pointColors,
                    pointRadius: pointRadii,
                    pointHoverRadius: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return ' Revenue: $' + context.parsed.y.toLocaleString();
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#928DAB' }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#928DAB',
                            callback: function (value) {
                                if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                                if (value >= 1000) return (value / 1000).toFixed(0) + 'k';
                                return value;
                            }
                        }
                    }
                }
            }
        });
    }

    // Close Modal
    const closeCompBtn = document.getElementById('closeCompModalBtn');
    if (closeCompBtn) {
        closeCompBtn.addEventListener('click', () => {
            document.getElementById('comparableModal').style.display = 'none';
        });
    }

    // --- FEEDBACK MODAL LOGIC ---
    const feedbackBtn = document.getElementById('feedbackBtn');
    const feedbackModal = document.getElementById('feedbackModal');
    const closeFeedbackBtn = document.getElementById('closeFeedbackBtn');
    const feedbackForm = document.getElementById('feedbackForm');
    const feedbackStatus = document.getElementById('feedbackStatus');

    if (feedbackBtn) {
        feedbackBtn.addEventListener('click', () => {
            feedbackModal.style.display = 'flex';
            feedbackStatus.textContent = '';
        });
    }

    if (closeFeedbackBtn) {
        closeFeedbackBtn.addEventListener('click', () => {
            feedbackModal.style.display = 'none';
        });
    }

    if (feedbackForm) {
        feedbackForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!currentPredictionData) {
                alert("Please run a prediction first to include data in the report.");
                return;
            }

            feedbackStatus.textContent = '📤 Sending report...';
            feedbackStatus.style.color = 'white';

            // Gather all inputs
            const payload = {
                comment: document.getElementById('feedbackComment').value,
                user_email: document.getElementById('loginEmail').value || "Guest",
                inputs: {
                    game_name: document.getElementById('gameName').value,
                    genre: genreSelect.value,
                    budget: document.getElementById('budget').value,
                    wishlists: document.getElementById('wishlists').value,
                    sentiment_target: document.getElementById('sentiment').value,
                    month: document.getElementById('month').value,
                    langs: document.getElementById('langs').value,
                    similar_games: document.getElementById('similarGames').value,
                    fixed_price: document.getElementById('fixedPrice').value,
                    prev_sales: document.getElementById('prevSales').value,
                    prev_score: document.getElementById('prevSentiment').value,
                    prev_buzz: document.getElementById('prevBuzz').value,
                    num_dlcs: document.getElementById('numDlcs').value,
                    dlc_price: document.getElementById('dlcPrice').value,
                    ia_buzz_score: currentSentimentScore
                },
                results: {
                    label: currentPredictionData.segment_label,
                    best_price: currentPredictionData.best_price,
                    max_profit: currentPredictionData.max_profit,
                    total_sales: currentPredictionData.est_total_sales,
                    evolution_years: currentPredictionData.evolution_years,
                    evolution_sales: currentPredictionData.evolution_sales
                }
            };

            try {
                const res = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    feedbackStatus.textContent = '✅ Report sent successfully!';
                    feedbackStatus.style.color = '#00ff88';
                    setTimeout(() => {
                        feedbackModal.style.display = 'none';
                        feedbackForm.reset();
                    }, 2000);
                } else {
                    feedbackStatus.textContent = '❌ Failed to send report.';
                    feedbackStatus.style.color = '#ff4444';
                }
            } catch (err) {
                feedbackStatus.textContent = '❌ Connection error.';
                feedbackStatus.style.color = '#ff4444';
            }
        });
    }

    // --- CUSTOM VALIDATION (English) ---
    const allInputs = document.querySelectorAll('input[required], select[required]');
    allInputs.forEach(input => {
        input.oninvalid = function(e) {
            e.target.setCustomValidity("");
            if (!e.target.validity.valid) {
                 e.target.setCustomValidity("Please enter a value for this required field.");
            }
        };
        input.oninput = function(e) {
            e.target.setCustomValidity("");
        };
    });

    // --- HISTORY LOGIC ---
    const historyBtn = document.getElementById('historyBtn');
    const historyModal = document.getElementById('historyModal');
    const closeHistory = document.getElementById('closeHistory');
    const historyListContainer = document.getElementById('historyListContainer');

    if (historyBtn) {
        historyBtn.addEventListener('click', async () => {
            const userId = window.currentUserId || localStorage.getItem('gamepredict_user_id');
            console.log("📜 Opening history for user:", userId);
            
            if (!userId) {
                alert("Please login again to access your history.");
                // Force return to landing if session lost
                document.getElementById('dashboardApp').style.display = 'none';
                document.getElementById('landingPage').style.display = 'block';
                return;
            }

            historyModal.style.display = 'flex';
            historyListContainer.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-muted);">Fetching your history...</p>';

            try {
                const url = `${API_BASE}/api/predictions/${userId}`;
                console.log("🔗 Fetching from:", url);
                
                const res = await fetch(url);
                const data = await res.json();
                console.log("📥 History data received:", data);

                if (res.ok) {
                    if (data.length === 0) {
                        historyListContainer.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-muted);">No saved predictions found.</p>';
                        return;
                    }

                    let html = `
                        <table class="history-table" style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                            <thead>
                                <tr style="border-bottom: 2px solid var(--glass-border); text-align: left;">
                                    <th style="padding: 12px; color: var(--text-muted);">DATE</th>
                                    <th style="padding: 12px; color: var(--text-muted);">GAME</th>
                                    <th style="padding: 12px; color: var(--text-muted);">PRICE</th>
                                    <th style="padding: 12px; color: var(--text-muted);">EST. SALES</th>
                                    <th style="padding: 12px; color: var(--text-muted);">ACTION</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    data.forEach(item => {
                        const date = new Date(item.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                        const itemJson = JSON.stringify(item).replace(/'/g, "&apos;").replace(/"/g, "&quot;");
                        html += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
                                <td style="padding: 15px; font-size: 0.85rem; color: var(--text-muted);">${date}</td>
                                <td style="padding: 15px; font-weight: 600;">${item.game_name || 'Unnamed Project'}</td>
                                <td style="padding: 15px; color: var(--primary); font-weight: bold;">$${item.fixed_price || item.best_price}</td>
                                <td style="padding: 15px; font-weight: bold;">${(item.est_total_sales || 0).toLocaleString()}</td>
                                <td style="padding: 15px;">
                                    <button class="btn-secondary history-load-btn" style="padding: 5px 12px; font-size: 0.8rem; background: rgba(0, 210, 255, 0.1); color: #00d2ff; border: 1px solid rgba(0, 210, 255, 0.2);" data-item='${itemJson}'>LOAD</button>
                                </td>
                            </tr>
                        `;
                    });

                    html += '</tbody></table>';
                    historyListContainer.innerHTML = html;

                    // Add listeners to load buttons
                    document.querySelectorAll('.history-load-btn').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            const itemData = JSON.parse(e.target.getAttribute('data-item'));
                            loadHistoryItem(itemData);
                        });
                    });
                } else {
                    console.error("❌ API Error:", data.message);
                    historyListContainer.innerHTML = `<p style="text-align: center; padding: 40px; color: #ff4444;">Server Error: ${data.message || 'Unknown error'}</p>`;
                }
            } catch (err) {
                console.error("❌ Catch Error:", err);
                historyListContainer.innerHTML = `<p style="text-align: center; padding: 40px; color: #ff4444;">Failed to connect to history service. (Check your internet or session)</p>`;
            }
        });
    }

    if (closeHistory) {
        closeHistory.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("✖ Closing history modal");
            historyModal.style.display = 'none';
        });
    }

    // Helper to load history item
    window.loadHistoryItem = function(item) {
        document.getElementById('gameName').value = item.game_name || '';
        document.getElementById('genreSelect').value = item.genre;
        document.getElementById('fixedPrice').value = item.fixed_price || '';
        document.getElementById('budget').value = item.budget;
        document.getElementById('wishlists').value = item.wishlists || '';
        document.getElementById('sentiment').value = item.sentiment_target || '';
        document.getElementById('month').value = item.month || '';
        document.getElementById('langs').value = item.langs || '';
        document.getElementById('similarGames').value = item.similar_games || '';
        document.getElementById('prevSales').value = item.previous_sales || '';
        document.getElementById('prevSentiment').value = item.previous_sentiment || '';
        document.getElementById('prevBuzz').value = item.previous_buzz || '';
        document.getElementById('numDlcs').value = item.num_dlcs || 0;
        document.getElementById('dlcPrice').value = item.dlc_price || 0;
        
        historyModal.style.display = 'none';
        
        // Visual cue
        const btn = document.querySelector('#predictionForm button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.innerHTML = "✨ RE-RUNNING...";
        btn.style.opacity = "0.7";
        
        setTimeout(() => {
            document.getElementById('predictionForm').dispatchEvent(new Event('submit'));
            btn.innerHTML = originalText;
            btn.style.opacity = "1";
        }, 800);
    };

    console.log("🚀 GamePredict.ai App Loaded / Version v51 active");
});
