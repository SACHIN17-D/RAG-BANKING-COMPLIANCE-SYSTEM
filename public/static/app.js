/**
 * ===================================================================
 * LOAN POLICY & CREDIT RISK RAG ASSISTANT - SINGLE DOCUMENT LOGIC
 * ===================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    let currentDocName = 'Loading...';
    let selectedFile = null;
    let dialogueHistory = []; // Multi-turn chat context memory

    // DOM Elements - Header & Status
    const activeDocNameText = document.getElementById('activeDocNameText');
    const openUploadModalBtn = document.getElementById('openUploadModalBtn');
    const statusPill = document.getElementById('statusPill');
    const statusText = document.getElementById('statusText');

    // DOM Elements - Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    // DOM Elements - Chat Assistant
    const chatHistory = document.getElementById('chatHistory');
    const chatForm = document.getElementById('chatForm');
    const queryInput = document.getElementById('queryInput');
    const sendBtn = document.getElementById('sendBtn');
    const topKInput = document.getElementById('topKInput');
    const minScoreSlider = document.getElementById('minScoreSlider');
    const minScoreValue = document.getElementById('minScoreValue');
    const clearChatBtn = document.getElementById('clearChatBtn');
    const exportReportBtn = document.getElementById('exportReportBtn');
    const presetChips = document.querySelectorAll('#presetChipsContainer .chip-btn');

    // DOM Elements - Vector Explorer
    const explorerQueryInput = document.getElementById('explorerQueryInput');
    const explorerSearchBtn = document.getElementById('explorerSearchBtn');
    const explorerResults = document.getElementById('explorerResults');

    // DOM Elements - System Config & Metrics
    const mDbStatus = document.getElementById('mDbStatus');
    const mChunkCount = document.getElementById('mChunkCount');
    const mEmbedModel = document.getElementById('mEmbedModel');
    const mEmbedDim = document.getElementById('mEmbedDim');
    const mLlmModel = document.getElementById('mLlmModel');
    const mGroqKey = document.getElementById('mGroqKey');
    const mPdfName = document.getElementById('mPdfName');
    const reindexBtn = document.getElementById('reindexBtn');
    const reindexStatus = document.getElementById('reindexStatus');

    // DOM Elements - Upload Modal
    const uploadModal = document.getElementById('uploadModal');
    const closeUploadModalBtn = document.getElementById('closeUploadModalBtn');
    const cancelUploadBtn = document.getElementById('cancelUploadBtn');
    const confirmUploadBtn = document.getElementById('confirmUploadBtn');
    const dropzone = document.getElementById('dropzone');
    const pdfFileInput = document.getElementById('pdfFileInput');
    const selectedFileName = document.getElementById('selectedFileName');
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadProgressBar = document.getElementById('uploadProgressBar');
    const uploadProgressText = document.getElementById('uploadProgressText');

    // =================================================================
    // 1. SYSTEM STATUS & ACTIVE DOCUMENT LOADER
    // =================================================================
    async function checkSystemStatus() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) throw new Error('Status endpoint failed');
            const data = await res.json();

            currentDocName = data.active_document || 'No Document';
            activeDocNameText.textContent = `${currentDocName} (${data.total_chunks} Chunks)`;

            statusPill.classList.add('online');
            statusText.textContent = `Ready (${data.total_chunks} Chunks)`;

            if (mDbStatus) mDbStatus.textContent = data.is_populated ? 'Populated & Active' : 'Empty (0 Chunks)';
            if (mChunkCount) mChunkCount.textContent = `${data.total_chunks} Indexed Vectors`;
            if (mEmbedModel) mEmbedModel.textContent = data.embedding_model;
            if (mEmbedDim) mEmbedDim.textContent = `${data.embedding_dimension}-dim Matryoshka`;
            if (mLlmModel) mLlmModel.textContent = data.llm_model;
            if (mGroqKey) mGroqKey.textContent = data.has_groq_api_key ? 'Groq API Key Active' : 'Missing GROQ_API_KEY';
            if (mPdfName) mPdfName.textContent = currentDocName;
        } catch (err) {
            console.error('Failed to fetch status:', err);
            statusPill.classList.remove('online');
            statusText.textContent = 'Offline / Error';
            if (mDbStatus) mDbStatus.textContent = 'Error connecting to API';
        }
    }

    // =================================================================
    // 2. DOCUMENT UPLOAD & REPLACE MODAL LOGIC
    // =================================================================
    openUploadModalBtn.addEventListener('click', () => {
        resetUploadModal();
        uploadModal.classList.add('active');
        loadServerDocuments();
    });

    closeUploadModalBtn.addEventListener('click', () => uploadModal.classList.remove('active'));
    cancelUploadBtn.addEventListener('click', () => uploadModal.classList.remove('active'));

    function resetUploadModal() {
        selectedFile = null;
        pdfFileInput.value = '';
        selectedFileName.textContent = '';
        confirmUploadBtn.disabled = true;
        uploadProgress.style.display = 'none';
        uploadProgressBar.style.width = '0%';
    }

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    pdfFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            alert('Please select a valid PDF document (.pdf).');
            return;
        }
        selectedFile = file;
        const mb = (file.size / (1024 * 1024)).toFixed(2);
        selectedFileName.innerHTML = `<i class="fa-solid fa-file-circle-check"></i> Ready to Replace: <strong>${escapeHtml(file.name)}</strong> (${mb} MB)`;
        confirmUploadBtn.disabled = false;
    }

    confirmUploadBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        confirmUploadBtn.disabled = true;
        uploadProgress.style.display = 'block';
        uploadProgressBar.style.width = '20%';
        uploadProgressText.textContent = 'Reading & encoding PDF...';

        try {
            // Read file as base64 string to ensure 100% reliable transport on Vercel & serverless
            const base64Content = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    const result = reader.result;
                    const base64 = result.includes(',') ? result.split(',')[1] : result;
                    resolve(base64);
                };
                reader.onerror = error => reject(error);
                reader.readAsDataURL(selectedFile);
            });

            uploadProgressBar.style.width = '55%';
            uploadProgressText.textContent = 'Uploading and generating semantic vector embeddings...';

            const res = await fetch('/api/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: selectedFile.name,
                    content_base64: base64Content
                })
            });

            const rawText = await res.text();
            let data = null;
            try {
                data = JSON.parse(rawText);
            } catch (e) {
                // Not valid JSON (e.g. 504 Gateway Timeout or 500 plain text from serverless proxy)
            }

            if (!res.ok) {
                const errorDetail = (data && data.detail) ? data.detail : (rawText || `Server responded with status ${res.status}`);
                throw new Error(errorDetail);
            }

            uploadProgressBar.style.width = '100%';
            uploadProgressText.textContent = `Success! Replaced policy (${data.total_chunks} chunks).`;

            setTimeout(async () => {
                uploadModal.classList.remove('active');
                await checkSystemStatus();
                dialogueHistory = [];
                showNotification(`Active policy updated to: ${data.active_document}`);
            }, 1000);

        } catch (err) {
            uploadProgressText.innerHTML = `<span style="color: var(--accent-rose)">Upload Error: ${escapeHtml(err.message)}</span>`;
            confirmUploadBtn.disabled = false;
        }
    });

    // =================================================================
    // 2B. SERVER-SIDE DOCUMENTS QUICK SWITCH
    // =================================================================
    async function loadServerDocuments() {
        const listEl = document.getElementById('serverDocsList');
        if (!listEl) return;
        listEl.innerHTML = '<span style="color:var(--text-muted); font-size:0.75rem;">Loading repository documents...</span>';
        try {
            const res = await fetch('/api/documents');
            if (!res.ok) throw new Error('Failed to load documents');
            const data = await res.json();
            const docs = data.documents || [];
            if (docs.length === 0) {
                listEl.innerHTML = '<span style="color:var(--text-muted); font-size:0.75rem;">No other documents in repository.</span>';
                return;
            }
            listEl.innerHTML = '';
            docs.forEach(doc => {
                const isActive = (doc.filename === currentDocName);
                const item = document.createElement('div');
                item.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.03); border:1px solid ' + (isActive ? 'var(--accent-teal)' : 'rgba(255,255,255,0.08)') + '; border-radius:6px; padding:6px 10px; font-size:0.8rem;';
                item.innerHTML = `
                    <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:70%;">
                        <i class="fa-solid fa-file-pdf" style="color:var(--accent-teal); margin-right:6px;"></i>
                        <strong>${escapeHtml(doc.filename)}</strong> <span style="color:var(--text-muted); font-size:0.75rem;">(${doc.size_mb} MB)</span>
                    </div>
                    <button class="select-doc-btn" data-file="${escapeHtml(doc.filename)}" ${isActive ? 'disabled style="opacity:0.6; cursor:default; background:transparent; color:var(--accent-teal); border:1px solid var(--accent-teal); padding:4px 8px; border-radius:4px; font-size:0.75rem;"' : 'style="background:var(--accent-blue); color:#fff; border:none; padding:4px 10px; border-radius:4px; font-size:0.75rem; cursor:pointer;"'}>
                        ${isActive ? '<i class="fa-solid fa-check"></i> Active' : '<i class="fa-solid fa-bolt"></i> Activate'}
                    </button>
                `;
                const btn = item.querySelector('.select-doc-btn');
                if (!isActive && btn) {
                    btn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        await activateServerDocument(doc.filename);
                    });
                }
                listEl.appendChild(item);
            });
        } catch (e) {
            listEl.innerHTML = `<span style="color:var(--accent-rose); font-size:0.75rem;">Failed to load documents</span>`;
        }
    }

    async function activateServerDocument(filename) {
        uploadProgress.style.display = 'block';
        uploadProgressBar.style.width = '50%';
        uploadProgressText.textContent = `Activating & indexing ${filename}...`;
        try {
            const res = await fetch('/api/select_document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Activation failed');
            uploadProgressBar.style.width = '100%';
            uploadProgressText.textContent = `Success! Activated ${filename} (${data.total_chunks} chunks).`;
            setTimeout(async () => {
                uploadModal.classList.remove('active');
                await checkSystemStatus();
                dialogueHistory = [];
                showNotification(`Active policy updated to: ${data.active_document}`);
            }, 1000);
        } catch (err) {
            uploadProgressText.innerHTML = `<span style="color: var(--accent-rose)">Error: ${escapeHtml(err.message)}</span>`;
        }
    }

    // =================================================================
    // 3. TABS SWITCHING LOGIC
    // =================================================================
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const activePanel = document.getElementById(targetTab);
            if (activePanel) activePanel.classList.add('active');
        });
    });

    // =================================================================
    // 4. CHAT PARAMETERS, PRESETS & AUDIT EXPORT
    // =================================================================
    minScoreSlider.addEventListener('input', (e) => {
        minScoreValue.textContent = parseFloat(e.target.value).toFixed(2);
    });

    queryInput.addEventListener('input', () => {
        queryInput.style.height = 'auto';
        queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + 'px';
    });

    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    clearChatBtn.addEventListener('click', () => {
        dialogueHistory = [];
        chatHistory.innerHTML = `
            <div class="welcome-card">
                <div class="welcome-icon"><i class="fa-solid fa-shield-halved"></i></div>
                <h2>CrediSense AI Underwriting Copilot</h2>
                <p>Ask any underwriting question, risk policy requirement, or loan structuring scenario. Every answer is generated strictly from the active policy manual ground truth with exact citations and zero hallucination.</p>
                <div class="feature-bullets">
                    <div><i class="fa-solid fa-circle-check"></i> <span>768-dim Asymmetric Nomic Vector Embeddings</span></div>
                    <div><i class="fa-solid fa-circle-check"></i> <span>Real-Time Token SSE Streaming & Multi-Turn Context</span></div>
                    <div><i class="fa-solid fa-circle-check"></i> <span>Page & Chunk Exact Citations</span></div>
                </div>
            </div>
        `;
    });

    if (exportReportBtn) {
        exportReportBtn.addEventListener('click', () => {
            if (dialogueHistory.length === 0) {
                alert('No conversation history to export yet.');
                return;
            }
            let mdContent = `# CrediSense AI — Credit Risk & Underwriting Audit Report\n`;
            mdContent += `**Active Policy Manual:** ${currentDocName}\n`;
            mdContent += `**Export Generated:** ${new Date().toLocaleString()}\n\n`;
            mdContent += `---\n\n`;

            dialogueHistory.forEach((turn, idx) => {
                if (turn.role === 'user') {
                    mdContent += `### Question #${Math.floor(idx / 2) + 1}: ${turn.content}\n\n`;
                } else if (turn.role === 'assistant') {
                    mdContent += `#### Grounded Explanation:\n${turn.content}\n\n`;
                    if (turn.sources && turn.sources.length > 0) {
                        mdContent += `*Citations (${turn.sources.length} matches):*\n`;
                        turn.sources.forEach(src => {
                            const meta = src.metadata || {};
                            mdContent += `- **${meta.source || currentDocName}** (Page ${meta.page || 'N/A'}, Chunk #${meta.chunk_index || 'N/A'}, Score: ${src.similarity_score}): ${src.document ? src.document.slice(0, 140) : ''}...\n`;
                        });
                        mdContent += `\n`;
                    }
                    mdContent += `---\n\n`;
                }
            });

            const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Loan_Policy_Audit_Report_${Date.now()}.md`;
            a.click();
            URL.revokeObjectURL(url);
        });
    }

    presetChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const query = chip.getAttribute('data-query');
            if (query) {
                queryInput.value = query;
                queryInput.style.height = 'auto';
                queryInput.style.height = queryInput.scrollHeight + 'px';
                submitChatQueryStream(query);
            }
        });
    });

    // =================================================================
    // 5. RAG CHAT STREAMING LOGIC
    // =================================================================
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (query) {
            submitChatQueryStream(query);
        }
    });

    async function submitChatQueryStream(queryText) {
        const welcomeCard = chatHistory.querySelector('.welcome-card');
        if (welcomeCard) welcomeCard.remove();

        appendUserMessage(queryText);
        dialogueHistory.push({ role: 'user', content: queryText });

        queryInput.value = '';
        queryInput.style.height = 'auto';
        sendBtn.disabled = true;

        const topK = parseInt(topKInput.value);
        const minScore = parseFloat(minScoreSlider.value);

        // Create Assistant Streaming Message Shell
        const assistantRow = document.createElement('div');
        assistantRow.className = 'message-row assistant';
        assistantRow.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-bubble">
                <div class="message-text"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>
                <div class="sources-placeholder"></div>
                <div class="meta-footer" style="display:none;">
                    <div class="timing-tag"><i class="fa-solid fa-stopwatch"></i> <span class="timing-text"></span></div>
                    <button class="copy-btn" onclick="navigator.clipboard.writeText(this.closest('.message-bubble').querySelector('.message-text').innerText); this.innerHTML='<i class=\\'fa-solid fa-check\\'></i> Copied!'; setTimeout(() => this.innerHTML='<i class=\\'fa-regular fa-copy\\'></i> Copy', 2000)">
                        <i class="fa-regular fa-copy"></i> Copy
                    </button>
                </div>
            </div>
        `;
        chatHistory.appendChild(assistantRow);
        scrollToBottom();

        const messageTextEl = assistantRow.querySelector('.message-text');
        const sourcesPlaceholderEl = assistantRow.querySelector('.sources-placeholder');
        const metaFooterEl = assistantRow.querySelector('.meta-footer');
        const timingTextEl = assistantRow.querySelector('.timing-text');

        let rawFullAnswer = '';
        let retrievedSources = [];

        try {
            const cleanHistory = dialogueHistory.slice(-6).map(h => ({
                role: h.role || 'user',
                content: typeof h.content === 'string' ? h.content : ''
            }));

            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: queryText,
                    top_k: topK,
                    min_score: minScore,
                    history: cleanHistory
                })
            });

            if (!response.ok) {
                throw new Error(`Server returned status ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (trimmedLine.startsWith('data: ')) {
                        const jsonStr = trimmedLine.slice(6);
                        try {
                            const eventData = JSON.parse(jsonStr);

                            if (eventData.type === 'sources') {
                                retrievedSources = eventData.sources || [];
                                renderSourcesSection(sourcesPlaceholderEl, retrievedSources, eventData.source_count, minScore);
                                messageTextEl.innerHTML = '';
                            } else if (eventData.type === 'token') {
                                rawFullAnswer += eventData.content;
                                messageTextEl.innerHTML = formatMarkdownText(rawFullAnswer);
                                scrollToBottom();
                            } else if (eventData.type === 'done') {
                                const timing = eventData.timing || {};
                                metaFooterEl.style.display = 'flex';
                                timingTextEl.textContent = `Retrieval: ${timing.retrieval_ms || 0}ms | Gen: ${timing.generation_ms || 0}ms | Total: ${timing.total_ms || 0}ms`;
                            }
                        } catch (e) {
                            console.error('SSE parse error:', e);
                        }
                    }
                }
            }

            dialogueHistory.push({ role: 'assistant', content: rawFullAnswer, sources: retrievedSources });

        } catch (err) {
            messageTextEl.innerHTML = `<span style="color: var(--accent-rose)">Error generating response: ${escapeHtml(err.message)}</span>`;
        } finally {
            sendBtn.disabled = false;
            scrollToBottom();
        }
    }

    function renderSourcesSection(container, sources, sourceCount, minScore) {
        if (!sources || sources.length === 0) {
            container.innerHTML = `
                <div class="sources-accordion">
                    <div class="sources-header">
                        <span><i class="fa-solid fa-circle-exclamation"></i> 0 Chunks passed Min Score (${minScore})</span>
                    </div>
                </div>
            `;
            return;
        }

        let cardsHtml = '';
        sources.forEach((item) => {
            const meta = item.metadata || {};
            const page = meta.page || 'N/A';
            const chunkIdx = meta.chunk_index || 'N/A';
            const sourceFile = meta.source || currentDocName;
            const score = item.similarity_score ? item.similarity_score.toFixed(4) : 'N/A';
            const snippet = item.document ? escapeHtml(item.document.slice(0, 320)) + '...' : '';

            cardsHtml += `
                <div class="source-card">
                    <div class="source-meta">
                        <span class="source-page"><i class="fa-solid fa-file-lines"></i> ${escapeHtml(sourceFile)} | Page ${page} (Chunk #${chunkIdx})</span>
                        <span class="score-badge">Score: ${score}</span>
                    </div>
                    <div class="source-snippet">${snippet}</div>
                </div>
            `;
        });

        container.innerHTML = `
            <div class="sources-accordion">
                <div class="sources-header" onclick="this.parentElement.classList.toggle('open')">
                    <span><i class="fa-solid fa-book-bookmark"></i> Ground Truth Policy Sources (${sources.length} Matches)</span>
                    <i class="fa-solid fa-chevron-down"></i>
                </div>
                <div class="sources-content">
                    ${cardsHtml}
                </div>
            </div>
        `;
    }

    function appendUserMessage(text) {
        const row = document.createElement('div');
        row.className = 'message-row user';
        row.innerHTML = `
            <div class="avatar"><i class="fa-solid fa-user"></i></div>
            <div class="message-bubble">
                <div class="message-text"><p>${escapeHtml(text)}</p></div>
            </div>
        `;
        chatHistory.appendChild(row);
    }

    // =================================================================
    // 6. VECTOR EXPLORER SEARCH LOGIC
    // =================================================================
    explorerSearchBtn.addEventListener('click', performExplorerSearch);
    explorerQueryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performExplorerSearch();
    });

    async function performExplorerSearch() {
        const query = explorerQueryInput.value.trim();
        if (!query) return;

        explorerResults.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-spinner fa-spin"></i>
                <p>Searching ChromaDB vector store for "${escapeHtml(currentDocName)}"...</p>
            </div>
        `;

        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, top_k: 10, min_score: 0.0 })
            });

            if (!res.ok) throw new Error('Search request failed');
            const data = await res.json();

            if (!data.results || data.results.length === 0) {
                explorerResults.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-box-open"></i>
                        <p>No matching vector chunks found for "${escapeHtml(query)}" in "${escapeHtml(currentDocName)}".</p>
                    </div>
                `;
                return;
            }

            let cardsHtml = '';
            data.results.forEach((item) => {
                const meta = item.metadata || {};
                const page = meta.page || 'N/A';
                const chunkIdx = meta.chunk_index || 'N/A';
                const sourceFile = meta.source || currentDocName;
                const score = item.similarity_score || 0;
                const scorePct = Math.round(score * 100);

                cardsHtml += `
                    <div class="explorer-card">
                        <div class="explorer-card-header">
                            <span class="explorer-page-badge"><i class="fa-solid fa-file-pdf"></i> ${escapeHtml(sourceFile)} | Page ${page} (Chunk Index ${chunkIdx})</span>
                            <div class="score-bar-container">
                                <span>Similarity Score: ${(score).toFixed(4)}</span>
                                <div class="score-bar-bg">
                                    <div class="score-bar-fill" style="width: ${scorePct}%"></div>
                                </div>
                            </div>
                        </div>
                        <div class="explorer-card-body">${escapeHtml(item.document)}</div>
                    </div>
                `;
            });

            explorerResults.innerHTML = cardsHtml;

        } catch (err) {
            explorerResults.innerHTML = `
                <div class="empty-state" style="color: var(--accent-rose)">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    <p>Search error: ${escapeHtml(err.message)}</p>
                </div>
            `;
        }
    }

    // =================================================================
    // 7. REINDEX ACTION LOGIC
    // =================================================================
    reindexBtn.addEventListener('click', async () => {
        if (!confirm(`Re-chunk and re-index '${currentDocName}' into ChromaDB?`)) return;

        reindexBtn.disabled = true;
        reindexStatus.innerHTML = '<span style="color: var(--accent-cyan)"><i class="fa-solid fa-spinner fa-spin"></i> Re-indexing PDF in background... Please wait.</span>';

        try {
            const res = await fetch('/api/reindex', { method: 'POST' });
            const rawText = await res.text();
            let data = null;
            try {
                data = JSON.parse(rawText);
            } catch (e) {}

            if (res.ok && data) {
                reindexStatus.innerHTML = `<span style="color: var(--accent-emerald)"><i class="fa-solid fa-circle-check"></i> ${data.message}</span>`;
                checkSystemStatus();
            } else {
                throw new Error((data && data.detail) ? data.detail : (rawText || `Reindexing failed (${res.status})`));
            }
        } catch (err) {
            reindexStatus.innerHTML = `<span style="color: var(--accent-rose)"><i class="fa-solid fa-triangle-exclamation"></i> ${err.message}</span>`;
        } finally {
            reindexBtn.disabled = false;
        }
    });

    // =================================================================
    // UTILITIES
    // =================================================================
    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatMarkdownText(text) {
        if (!text) return '';
        let html = escapeHtml(text);
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        const lines = html.split('\n');
        let inList = false;
        let resultLines = [];

        lines.forEach(line => {
            const trimmed = line.trim();
            if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                if (!inList) {
                    inList = true;
                    resultLines.push('<ul>');
                }
                resultLines.push(`<li>${trimmed.slice(2)}</li>`);
            } else {
                if (inList) {
                    inList = false;
                    resultLines.push('</ul>');
                }
                if (trimmed) {
                    resultLines.push(`<p>${trimmed}</p>`);
                }
            }
        });

        if (inList) resultLines.push('</ul>');
        return resultLines.join('');
    }

    function showNotification(msg) {
        const notif = document.createElement('div');
        notif.className = 'toast-notification';
        notif.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${escapeHtml(msg)}`;
        document.body.appendChild(notif);
        setTimeout(() => notif.classList.add('show'), 10);
        setTimeout(() => {
            notif.classList.remove('show');
            setTimeout(() => notif.remove(), 300);
        }, 3000);
    }

    // Initialize system status on page load
    checkSystemStatus();
});
