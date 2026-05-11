// Word Counter JavaScript
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileDisplayContainer = document.getElementById('fileDisplayContainer');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const textInput = document.getElementById('textInput');
    const charCountDisplay = document.getElementById('charCountDisplay');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultsSection = document.getElementById('resultsSection');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const newAnalysisBtn = document.getElementById('newAnalysisBtn');

    // Update character count in real-time
    textInput.addEventListener('input', () => {
        charCountDisplay.textContent = textInput.value.length;
    });

    // Drag and Drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-active'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-active'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            showFileName();
        }
    });

    fileInput.addEventListener('change', showFileName);

    dropZone.addEventListener('click', (e) => {
        if (e.target !== fileInput && !removeFileBtn.contains(e.target)) {
            fileInput.click();
        }
    });

    function showFileName() {
        if (fileInput.files.length > 0) {
            fileNameDisplay.innerHTML = '';
            for (let i = 0; i < fileInput.files.length; i++) {
                const file = fileInput.files[i];
                const icon = file.name.endsWith('.docx') ? '📝' : '📄';
                fileNameDisplay.innerHTML += `<span class="inline-block bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 px-3 py-1 rounded-full text-xs font-semibold">${icon} ${file.name}</span>`;
            }
            fileDisplayContainer.classList.remove('hidden');
        } else {
            fileDisplayContainer.classList.add('hidden');
        }
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.value = '';
            fileDisplayContainer.classList.add('hidden');
            fileNameDisplay.innerHTML = '';
        });
    }

    // Read file content if needed (for TXT files)
    async function readFileContent(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file);
        });
    }

    // Analyze button click
    analyzeBtn.addEventListener('click', async () => {
        errorAlert.classList.add('hidden');

        const text = textInput.value.trim();
        const files = fileInput.files;

        if (!text && files.length === 0) {
            showError('Por favor introduce texto o selecciona un archivo para analizar.');
            return;
        }

        // Show loading state
        const originalBtnContent = analyzeBtn.innerHTML;
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Analizando...';

        const formData = new FormData();
        formData.append('text', text);

        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput) {
            showError('CSRF token no encontrado');
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = originalBtnContent;
            return;
        }

        try {
            const response = await fetch('/word-counter/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfInput.value },
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Error al analizar el texto');
            }

            const data = await response.json();
            displayResults(data);

        } catch (error) {
            showError(error.message);
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = originalBtnContent;
        }
    });

    function displayResults(data) {
        // Update stats
        document.getElementById('wordCount').textContent = data.word_count.toLocaleString();
        document.getElementById('uniqueWords').textContent = data.unique_words.toLocaleString();
        document.getElementById('charCount').textContent = data.char_count.toLocaleString();
        document.getElementById('charCountNoSpaces').textContent = data.char_count_no_spaces.toLocaleString();
        document.getElementById('sentenceCount').textContent = data.sentence_count.toLocaleString();
        document.getElementById('paragraphCount').textContent = data.paragraph_count.toLocaleString();
        document.getElementById('avgWordLength').textContent = data.avg_word_length;
        document.getElementById('textPreview').textContent = data.text_preview;

        // Most common words table
        const tbody = document.getElementById('mostCommonWordsBody');
        tbody.innerHTML = '';

        if (data.most_common && data.most_common.length > 0) {
            const maxFreq = data.most_common[0][1];

            data.most_common.forEach(([word, freq]) => {
                const percentage = (freq / maxFreq) * 100;
                const row = document.createElement('tr');
                row.className = 'hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors';
                row.innerHTML = `
                    <td class="py-3 px-4 text-sm text-slate-700 dark:text-slate-300 font-medium">${word}</td>
                    <td class="py-3 px-4 text-sm text-slate-600 dark:text-slate-400">${freq}</td>
                    <td class="py-3 px-4">
                        <div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                            <div class="bg-gradient-to-r from-emerald-500 to-teal-500 h-2 rounded-full transition-all duration-500" style="width: ${percentage}%"></div>
                        </div>
                    </td>
                `;
                tbody.appendChild(row);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="3" class="py-4 text-center text-slate-500 dark:text-slate-400">No se encontraron palabras</td></tr>';
        }

        // Show results section
        resultsSection.classList.remove('hidden');

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorAlert.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // New analysis button
    if (newAnalysisBtn) {
        newAnalysisBtn.addEventListener('click', () => {
            textInput.value = '';
            charCountDisplay.textContent = '0';
            fileInput.value = '';
            fileDisplayContainer.classList.add('hidden');
            fileNameDisplay.innerHTML = '';
            resultsSection.classList.add('hidden');
            errorAlert.classList.add('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
});
