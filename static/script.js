document.addEventListener('DOMContentLoaded', () => {

    // ── DOM refs ──────────────────────────────────────────────────────────────
    const toolCards         = document.querySelectorAll('.tool-card');
    const getStartedBtn     = document.getElementById('get-started-btn');
    const uploadSection     = document.getElementById('upload-section');
    const selectedToolTitle = document.getElementById('selected-tool-title');
    const toolInstruction   = document.getElementById('tool-instruction');
    const toolOptions       = document.getElementById('tool-options');
    const dropZone          = document.getElementById('drop-zone');
    const fileInput         = document.getElementById('file-input');
    const selectFilesBtn    = document.getElementById('select-files-btn');
    const fileList          = document.getElementById('file-list');
    const actionArea        = document.getElementById('action-area');
    const convertBtn        = document.getElementById('convert-btn');
    const btnText           = document.getElementById('btn-text');
    const btnSpinner        = document.getElementById('btn-spinner');
    const statusMessage     = document.getElementById('status-message');
    const downloadArea      = document.getElementById('download-area');
    const downloadBtn       = document.getElementById('download-btn');
    const resetBtn          = document.getElementById('reset-btn');
    const infoResult        = document.getElementById('info-result');
    const compressionResult = document.getElementById('compression-result');
    const hamburger         = document.getElementById('hamburger');
    const navLinks          = document.querySelector('.nav-links');

    let currentTool    = null;
    let acceptTypes    = '';
    let allowMultiple  = false;
    let selectedFiles  = [];

    // ── Tool option templates ─────────────────────────────────────────────────
    const toolOptionTemplates = {
        compress: `
            <div class="options-panel">
                <label for="target-size">Target file size (MB) — optional</label>
                <input type="number" id="target-size" min="0.1" step="0.1" placeholder="e.g. 1.5">
            </div>`,
        split: `
            <div class="options-panel">
                <label for="page-ranges">Pages to extract (leave blank for all)</label>
                <input type="text" id="page-ranges" placeholder="e.g. 1-3, 5, 7-9">
                <p style="font-size:0.8rem;color:#94a3b8;margin-top:0.4rem;">Examples: <code>1-3</code> = pages 1 to 3 &nbsp;|&nbsp; <code>1,3,5</code> = individual pages</p>
            </div>`,
        rotate: `
            <div class="options-panel">
                <label for="rotate-angle">Rotation angle</label>
                <select id="rotate-angle">
                    <option value="90">90° Clockwise</option>
                    <option value="180">180°</option>
                    <option value="270">90° Counter-clockwise (270°)</option>
                </select>
            </div>`,
        watermark: `
            <div class="options-panel">
                <div class="options-row">
                    <div>
                        <label for="wm-text">Watermark text</label>
                        <input type="text" id="wm-text" placeholder="e.g. CONFIDENTIAL" value="CONFIDENTIAL">
                    </div>
                    <div>
                        <label>Text color</label>
                        <div class="color-row">
                            <input type="color" id="wm-color" value="#FF0000">
                            <span id="wm-color-label" style="font-size:0.85rem;color:#64748b;">#FF0000</span>
                        </div>
                    </div>
                </div>
                <div style="margin-top:1rem;">
                    <div class="range-label">
                        <label for="wm-opacity">Opacity</label>
                        <span id="wm-opacity-label">30%</span>
                    </div>
                    <input type="range" id="wm-opacity" min="5" max="100" value="30">
                </div>
            </div>`,
        protect: `
            <div class="options-panel">
                <div class="options-row">
                    <div>
                        <label for="pdf-password">Password</label>
                        <input type="password" id="pdf-password" placeholder="Enter password" autocomplete="new-password">
                    </div>
                    <div>
                        <label for="pdf-password-confirm">Confirm password</label>
                        <input type="password" id="pdf-password-confirm" placeholder="Re-enter password">
                    </div>
                </div>
            </div>`,
        unlock: `
            <div class="options-panel">
                <label for="unlock-password">PDF Password</label>
                <input type="password" id="unlock-password" placeholder="Enter the PDF's current password">
            </div>`,
    };

    // ── Hero parallax ─────────────────────────────────────────────────────────
    const hero = document.querySelector('.hero');
    const heroContent = document.querySelector('.hero-content');
    if (hero && heroContent) {
        hero.addEventListener('mousemove', (e) => {
            const xPos = (e.clientX / window.innerWidth - 0.5) * 2;
            const yPos = (e.clientY / window.innerHeight - 0.5) * 2;
            heroContent.style.transform = `translate(${xPos * 10}px, ${yPos * 10}px)`;
            hero.style.setProperty('--mouseX', `${xPos * 20}px`);
            hero.style.setProperty('--mouseY', `${yPos * 20}px`);
        });
        hero.addEventListener('mouseleave', () => {
            heroContent.style.transform = '';
            hero.style.setProperty('--mouseX', '0px');
            hero.style.setProperty('--mouseY', '0px');
        });
    }

    // ── Get Started scroll ────────────────────────────────────────────────────
    getStartedBtn.addEventListener('click', () => {
        document.getElementById('tools-section').scrollIntoView({ behavior: 'smooth' });
    });

    // ── Hamburger ─────────────────────────────────────────────────────────────
    hamburger.addEventListener('click', () => navLinks.classList.toggle('open'));

    // ── FAQ accordion ─────────────────────────────────────────────────────────
    document.querySelectorAll('.faq-question').forEach(btn => {
        btn.addEventListener('click', () => {
            const item = btn.parentElement;
            const wasOpen = item.classList.contains('open');
            document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
            if (!wasOpen) item.classList.add('open');
        });
    });

    // ── Tool card 3D tilt ─────────────────────────────────────────────────────
    toolCards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const rotateX = (((e.clientY - rect.top) / rect.height) - 0.5) * -14;
            const rotateY = (((e.clientX - rect.left) / rect.width) - 0.5) * 14;
            card.style.transition = 'transform 0.1s ease-out, box-shadow 0.1s ease-out';
            card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px)`;
            card.style.zIndex = '10';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transition = 'all 0.4s cubic-bezier(0.175,0.885,0.32,1.275)';
            card.style.transform = card.classList.contains('selected') ? 'translateY(-5px)' : '';
            card.style.zIndex = '1';
        });
    });

    // ── Select tool ───────────────────────────────────────────────────────────
    toolCards.forEach(card => {
        card.addEventListener('click', () => {
            toolCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');

            currentTool   = card.dataset.tool;
            acceptTypes   = card.dataset.accept;
            allowMultiple = card.dataset.multiple === 'true';

            selectedToolTitle.textContent = card.querySelector('h3').textContent;

            const instructions = {
                'merge'        : 'Upload 2 or more PDF files to merge them into one.',
                'split'        : 'Upload a PDF and optionally specify which pages to extract.',
                'compress'     : 'Upload a PDF to reduce its file size.',
                'rotate'       : 'Upload a PDF and choose the rotation angle.',
                'watermark'    : 'Upload a PDF and customise your watermark text.',
                'protect'      : 'Upload a PDF and set a password to protect it.',
                'unlock'       : 'Upload a password-protected PDF to remove its password.',
                'extract-text' : 'Upload a PDF to extract all text content as a .txt file.',
                'pdf-info'     : 'Upload a PDF to view its page count, metadata and file details.',
                'jpg-to-pdf'   : 'Upload one or more JPG/PNG images to combine them into a PDF.',
                'pdf-to-jpg'   : 'Upload a PDF to convert each page into a JPG image.',
                'pdf-to-word'  : 'Upload a PDF to convert it into an editable Word document.',
                'word-to-pdf'  : 'Upload a Word document (.doc/.docx) to convert it to PDF.',
            };
            toolInstruction.textContent = instructions[currentTool] || `Upload files to use ${selectedToolTitle.textContent}.`;

            // Inject tool-specific options
            toolOptions.innerHTML = toolOptionTemplates[currentTool] || '';

            // Live watermark listeners
            if (currentTool === 'watermark') {
                const colorInput   = document.getElementById('wm-color');
                const colorLabel   = document.getElementById('wm-color-label');
                const opacityInput = document.getElementById('wm-opacity');
                const opacityLabel = document.getElementById('wm-opacity-label');
                colorInput.addEventListener('input', () => { colorLabel.textContent = colorInput.value; });
                opacityInput.addEventListener('input', () => { opacityLabel.textContent = opacityInput.value + '%'; });
            }

            // Enable drop zone
            dropZone.style.pointerEvents = 'auto';
            dropZone.style.opacity = '1';
            dropZone.classList.add('active');
            fileInput.accept = acceptTypes;
            allowMultiple ? fileInput.setAttribute('multiple', '') : fileInput.removeAttribute('multiple');

            // Reset state
            selectedFiles = [];
            updateFileList();
            clearStatus();
            downloadArea.classList.add('hidden');
            infoResult.classList.add('hidden');
            compressionResult.classList.add('hidden');
            convertBtn.classList.remove('hidden');

            // Rename button for info tool
            btnText.textContent = currentTool === 'pdf-info' ? 'Analyse PDF' : 'Convert Now';

            uploadSection.scrollIntoView({ behavior: 'smooth' });
        });
    });

    // ── File input triggers ───────────────────────────────────────────────────
    selectFilesBtn.addEventListener('click', () => {
        if (!currentTool) return showError('Please select a tool first.');
        fileInput.click();
    });
    fileInput.addEventListener('change', (e) => { handleFiles(e.target.files); fileInput.value = ''; });

    // ── Drag & drop ───────────────────────────────────────────────────────────
    ['dragenter','dragover','dragleave','drop'].forEach(ev => dropZone.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); }));
    ['dragenter','dragover'].forEach(ev => dropZone.addEventListener(ev, () => { if (currentTool) dropZone.classList.add('dragover'); }));
    ['dragleave','drop'].forEach(ev => dropZone.addEventListener(ev, () => dropZone.classList.remove('dragover')));
    dropZone.addEventListener('drop', (e) => {
        if (!currentTool) return showError('Please select a tool first.');
        handleFiles(e.dataTransfer.files);
    });

    // ── Handle files ──────────────────────────────────────────────────────────
    function handleFiles(files) {
        clearStatus();
        const validExtensions = acceptTypes.split(',').map(ext => ext.trim().toLowerCase());
        let validFiles = Array.from(files).filter(file => {
            const isValid = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
            if (!isValid) showError(`Invalid file type: ${file.name}. Expected: ${acceptTypes}`);
            return isValid;
        });
        if (!validFiles.length) return;
        selectedFiles = allowMultiple ? [...selectedFiles, ...validFiles] : [validFiles[0]];
        updateFileList();
    }

    function updateFileList() {
        downloadArea.classList.add('hidden');
        infoResult.classList.add('hidden');
        compressionResult.classList.add('hidden');
        convertBtn.classList.remove('hidden');
        fileList.innerHTML = '';

        if (selectedFiles.length > 0) {
            actionArea.classList.remove('hidden');
            selectedFiles.forEach((file, index) => {
                const ext = file.name.toLowerCase();
                let iconClass = 'fa-file';
                if (ext.endsWith('.pdf')) iconClass = 'fa-file-pdf';
                else if (ext.match(/\.(doc|docx)$/)) iconClass = 'fa-file-word';
                else if (ext.match(/\.(jpg|jpeg|png)$/)) iconClass = 'fa-image';

                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <div class="file-info">
                        <i class="fa-solid ${iconClass}"></i>
                        <span>${file.name}</span>
                        <span style="color:#94a3b8;font-size:0.8rem;font-weight:400;">(${formatSize(file.size)})</span>
                    </div>
                    <button class="remove-btn" data-index="${index}"><i class="fa-solid fa-xmark"></i></button>`;
                fileList.appendChild(item);
            });
            document.querySelectorAll('.remove-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    selectedFiles.splice(parseInt(e.currentTarget.dataset.index), 1);
                    updateFileList();
                });
            });
        } else {
            actionArea.classList.add('hidden');
        }
    }

    // ── Convert ───────────────────────────────────────────────────────────────
    convertBtn.addEventListener('click', async () => {
        if (!currentTool) return showError('Please select a tool first.');
        if (!selectedFiles.length) return showError('Please upload at least one file.');
        if ((currentTool === 'merge' || currentTool === 'jpg-to-pdf') && selectedFiles.length < 2) {
            return showError('Please select at least 2 files for this operation.');
        }

        // Validate passwords
        if (currentTool === 'protect') {
            const pw  = document.getElementById('pdf-password').value;
            const pw2 = document.getElementById('pdf-password-confirm').value;
            if (!pw) return showError('Please enter a password.');
            if (pw !== pw2) return showError('Passwords do not match.');
        }
        if (currentTool === 'unlock') {
            if (!document.getElementById('unlock-password').value) return showError('Please enter the PDF password.');
        }

        setLoading(true);
        showStatus('Uploading files…', 'loading');

        try {
            // 1. Upload
            const formData = new FormData();
            selectedFiles.forEach(file => formData.append('files[]', file));
            const uploadRes = await fetch('/upload', { method: 'POST', body: formData });
            if (!uploadRes.ok) throw new Error('Upload failed.');
            const uploadData = await uploadRes.json();
            if (uploadData.error) throw new Error(uploadData.error);
            const serverFilenames = uploadData.files;

            // 2. Build endpoint & payload
            let endpoint;
            const endpoints = {
                'merge': '/merge', 'split': '/split', 'compress': '/compress',
                'rotate': '/rotate', 'watermark': '/watermark',
                'protect': '/protect', 'unlock': '/unlock',
                'extract-text': '/extract-text', 'pdf-info': '/pdf-info',
            };
            endpoint = endpoints[currentTool] || `/convert/${currentTool}`;

            const payload = allowMultiple ? { filenames: serverFilenames } : { filename: serverFilenames[0] };

            if (currentTool === 'compress') {
                const ts = document.getElementById('target-size')?.value;
                if (ts) payload.target_size = parseFloat(ts);
            }
            if (currentTool === 'split') {
                const pr = document.getElementById('page-ranges')?.value;
                if (pr) payload.page_ranges = pr;
            }
            if (currentTool === 'rotate') {
                payload.angle = parseInt(document.getElementById('rotate-angle').value);
            }
            if (currentTool === 'watermark') {
                payload.text    = document.getElementById('wm-text').value || 'CONFIDENTIAL';
                payload.color   = document.getElementById('wm-color').value;
                payload.opacity = parseInt(document.getElementById('wm-opacity').value) / 100;
            }
            if (currentTool === 'protect') {
                payload.password = document.getElementById('pdf-password').value;
            }
            if (currentTool === 'unlock') {
                payload.password = document.getElementById('unlock-password').value;
            }

            showStatus('Processing…', 'loading');
            const processRes  = await fetch(endpoint, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const processData = await processRes.json();
            if (!processRes.ok) throw new Error(processData.error || 'Processing failed.');

            setLoading(false);

            // ── PDF Info: show info panel instead of download ──
            if (currentTool === 'pdf-info') {
                showStatus('Analysis complete!', 'success');
                convertBtn.classList.add('hidden');
                renderInfoPanel(processData.info);
                return;
            }

            // ── Compress: show savings ──
            if (currentTool === 'compress' && processData.original_size && processData.new_size) {
                renderCompressionResult(processData.original_size, processData.new_size);
            }

            // Show download
            showStatus('Your file is ready!', 'success');
            convertBtn.classList.add('hidden');
            downloadBtn.href = processData.download_url;
            downloadArea.classList.remove('hidden');

        } catch (err) {
            showError(err.message);
            setLoading(false);
        }
    });

    // ── Reset ─────────────────────────────────────────────────────────────────
    resetBtn.addEventListener('click', () => {
        selectedFiles = [];
        updateFileList();
        clearStatus();
        downloadArea.classList.add('hidden');
        infoResult.classList.add('hidden');
        compressionResult.classList.add('hidden');
        convertBtn.classList.remove('hidden');
        btnText.textContent = currentTool === 'pdf-info' ? 'Analyse PDF' : 'Convert Now';
    });

    // ── Render helpers ────────────────────────────────────────────────────────
    function renderInfoPanel(info) {
        infoResult.innerHTML = `
            <h3><i class="fa-solid fa-circle-info" style="margin-right:0.5rem;"></i>PDF Information</h3>
            <div class="info-grid">
                <div class="info-item"><div class="label">Pages</div><div class="value">${info.page_count}</div></div>
                <div class="info-item"><div class="label">File Size</div><div class="value">${info.file_size_kb} KB</div></div>
                <div class="info-item"><div class="label">Title</div><div class="value">${info.title}</div></div>
                <div class="info-item"><div class="label">Author</div><div class="value">${info.author}</div></div>
                <div class="info-item"><div class="label">Creator</div><div class="value">${info.creator}</div></div>
                <div class="info-item"><div class="label">Encrypted</div><div class="value">${info.encrypted ? '🔒 Yes' : '🔓 No'}</div></div>
                ${info.page_width_pt ? `<div class="info-item"><div class="label">Page Width</div><div class="value">${info.page_width_pt} pt</div></div>` : ''}
                ${info.page_height_pt ? `<div class="info-item"><div class="label">Page Height</div><div class="value">${info.page_height_pt} pt</div></div>` : ''}
            </div>`;
        infoResult.classList.remove('hidden');
    }

    function renderCompressionResult(originalBytes, newBytes) {
        const orig    = (originalBytes / 1024 / 1024).toFixed(2);
        const newSz   = (newBytes / 1024 / 1024).toFixed(2);
        const savings = Math.max(0, Math.round((1 - newBytes / originalBytes) * 100));
        const barPct  = Math.round((newBytes / originalBytes) * 100);
        compressionResult.innerHTML = `
            <h3><i class="fa-solid fa-compress" style="margin-right:0.5rem;"></i>Compression Result</h3>
            <div class="info-grid">
                <div class="info-item"><div class="label">Original Size</div><div class="value">${orig} MB</div></div>
                <div class="info-item"><div class="label">New Size</div><div class="value">${newSz} MB</div></div>
                <div class="info-item"><div class="label">Saved</div><div class="value" style="color:var(--success);">${savings}%</div></div>
            </div>
            <div class="compression-bar">
                <div class="bar-labels"><span>0 MB</span><span>${orig} MB</span></div>
                <div class="bar-track"><div class="bar-fill" style="width:${barPct}%"></div></div>
            </div>`;
        compressionResult.classList.remove('hidden');
    }

    // ── Utilities ─────────────────────────────────────────────────────────────
    function showError(msg) { statusMessage.textContent = msg; statusMessage.className = 'status-message error'; }
    function showStatus(msg, type) { statusMessage.textContent = msg; statusMessage.className = `status-message ${type}`; }
    function clearStatus() { statusMessage.textContent = ''; statusMessage.className = 'status-message'; }
    function setLoading(isLoading) {
        convertBtn.disabled = isLoading;
        if (isLoading) { btnText.textContent = 'Processing…'; btnSpinner.classList.remove('hidden'); }
        else { btnText.textContent = currentTool === 'pdf-info' ? 'Analyse PDF' : 'Convert Now'; btnSpinner.classList.add('hidden'); }
    }
    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1024 / 1024).toFixed(2) + ' MB';
    }
});
