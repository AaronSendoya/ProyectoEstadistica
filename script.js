
    // Inyección de checkboxes de posición
    const cContainer = document.querySelector('#cuartilesContainer');
    for (let i = 1; i <= 4; i++) {
        cContainer.innerHTML += `<label class="flex items-center hover:bg-slate-50 p-1 rounded transition-colors cursor-pointer"><input type="checkbox" name="metrics[]" value="cuartil_${i}" class="form-checkbox h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"> <span class="ml-2 text-sm font-medium text-slate-700">Cuartil ${i}</span></label>`;
    }

    const dContainer = document.querySelector('#decilesContainer .grid');
    for (let i = 1; i <= 9; i++) {
        dContainer.innerHTML += `<label class="flex items-center hover:bg-slate-50 p-1 rounded transition-colors cursor-pointer"><input type="checkbox" name="metrics[]" value="decil_${i}" class="form-checkbox h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"> <span class="ml-2 text-sm font-medium text-slate-700">Decil ${i}</span></label>`;
    }

    const pContainer = document.querySelector('#percentilesContainer .grid');
    for (let i = 1; i <= 99; i++) {
        pContainer.innerHTML += `<label class="flex items-center hover:bg-slate-50 p-1 rounded transition-colors cursor-pointer"><input type="checkbox" name="metrics[]" value="percentil_${i}" class="form-checkbox h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"> <span class="ml-2 text-sm font-medium text-slate-700">Percentil ${i}</span></label>`;
    }

    const form = document.getElementById('analysisForm');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileDisplayContainer = document.getElementById('fileDisplayContainer');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const submitBtn = document.getElementById('submitBtn');

    // Manejo de "Seleccionar todo"
    const selectAllMetricsBtn = document.getElementById('selectAllMetrics');
    const metricCheckboxesList = document.querySelectorAll('input[name="metrics[]"]');

    if (selectAllMetricsBtn) {
        selectAllMetricsBtn.addEventListener('change', function () {
            const isChecked = this.checked;
            metricCheckboxesList.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        });

        metricCheckboxesList.forEach(checkbox => {
            checkbox.addEventListener('change', function () {
                const allChecked = Array.from(metricCheckboxesList).every(c => c.checked);
                selectAllMetricsBtn.checked = allChecked;
            });
        });
    }

    // Manejo de Drag and Drop Visual
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

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

    // Al hacer click en cualquier parte de la zona, abrimos el browser
    dropZone.addEventListener('click', (e) => {
        if (e.target !== fileInput && !removeFileBtn.contains(e.target)) fileInput.click();
    });


    // Global available columns
    let availableColumns = [];

    // Lógica para añadir filas variables
    function updateVarLimit() {
        const list = document.getElementById('variablesList');
        const count = list.children.length;
        const btn = document.getElementById('btnAddVariable');
        const msg = document.getElementById('varLimitMsg');

        if (count >= 5) {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
            msg.classList.remove('hidden');
        } else {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
            msg.classList.add('hidden');
        }
    }

    function addVariableRow() {
        const list = document.getElementById('variablesList');
        if (list.children.length >= 5) return;

        const row = document.createElement('div');
        row.className = "flex gap-3 items-center row-variable bg-slate-50 p-2 rounded-lg border border-slate-200 shadow-sm";

        let colsOpts = availableColumns.map(c => `<option value="${c}">${c}</option>`).join('');

        row.innerHTML = `
            <select class="var-col form-select flex-1 bg-white border border-slate-300 text-slate-700 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow text-sm">
                ${colsOpts}
            </select>
            <select class="var-chart form-select w-40 bg-white border border-slate-300 text-slate-700 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow text-sm">
                <option value="bar">Columnas</option>
                <option value="line">Lineal</option>
                <option value="pie">Circular</option>
                <option value="scatter">Dispersión</option>
            </select>
            <button type="button" class="btn-remove-var text-slate-400 hover:text-red-500 hover:bg-red-50 p-1.5 rounded-md transition-colors border border-transparent">
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        `;

        row.querySelector('.btn-remove-var').addEventListener('click', () => {
            row.remove();
            updateVarLimit();
        });

        list.appendChild(row);
        updateVarLimit();
    }

    document.getElementById('btnAddVariable').addEventListener('click', addVariableRow);

    async function fetchColumnsForFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const columnSelectionContainer = document.getElementById('variableBuilderContainer');

        try {
            const resp = await fetch('/api/columns/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                body: formData
            });

            if (resp.ok) {
                const data = await resp.json();
                if (data.columns && data.columns.length > 0) {
                    availableColumns = data.columns;
                    document.getElementById('variablesList').innerHTML = ''; // Limpiar anteriores
                    addVariableRow(); // add first by default
                    columnSelectionContainer.classList.remove('hidden');
                }
            } else {
                console.error("Error API:", await resp.json());
            }
        } catch (e) {
            console.error("Error fetching columns", e);
        }
    }

    function showFileName() {
        if (fileInput.files.length > 0) {
            fileNameDisplay.textContent = '📦 Archivo: ' + fileInput.files[0].name;
            fileDisplayContainer.classList.remove('hidden');
            fetchColumnsForFile(fileInput.files[0]);
        } else {
            fileDisplayContainer.classList.add('hidden');
            const colContainer = document.getElementById('columnSelectionContainer');
            if (colContainer) colContainer.classList.add('hidden');
        }
    }

    removeFileBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        // Reset file input
        fileInput.value = '';

        // Reset visual state
        fileDisplayContainer.classList.add('hidden');

        // Clear errors
        errorAlert.classList.add('hidden');
        errorMessage.textContent = '';
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorAlert.classList.add('hidden');

        if (!fileInput.files.length) {
            showError("Por favor selecciona un documento para iniciar el análisis.");
            return;
        }

        const checkedBoxOptions = document.querySelectorAll('input[name="metrics[]"]:checked');
        if (checkedBoxOptions.length === 0) {
            showError("Debes seleccionar al menos una métrica a calcular en el paso 2.");
            return;
        }

        // RECOLECCIÓN DEL FORMULARIO
        const formData = new FormData();

        // 1. Archivo
        formData.append('file', fileInput.files[0]);

        // 2. Metricas
        checkedBoxOptions.forEach(checkbox => {
            formData.append('metrics[]', checkbox.value);
        });

        // 3. Format & Layout
        const formatSelect = document.querySelector('input[name="format"]:checked');
        const format = formatSelect ? formatSelect.value : 'excel';
        formData.append('format', format);

        const layoutSelect = document.querySelector('input[name="layout"]:checked');
        const layout = layoutSelect ? layoutSelect.value : 'horizontal';
        formData.append('layout', layout);

        // 4. Detail Level
        const detailLevel = document.getElementById('detailLevel');
        if (detailLevel) {
            formData.append('detail_level', detailLevel.value);
        }

        // 5. Array Complejo Multi-Variable
        const rows = document.querySelectorAll('.row-variable');
        if (rows.length === 0) {
            showError("Debe añadir al menos una variable en el constructor.");
            return;
        }

        let variablesArr = [];
        rows.forEach(r => {
            variablesArr.push({
                columna: r.querySelector('.var-col').value,
                grafico: r.querySelector('.var-chart').value
            });
        });
        formData.append('variables', JSON.stringify(variablesArr));

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Procesando Múltiples Variables...';

        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        try {
            const response = await fetch('/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Error interno del servidor Django.');
            }

            const data = await response.json();

            // Transición a vista previa visual
            form.classList.add('hidden');
            const previewContainer = document.getElementById('previewContainer');
            previewContainer.classList.remove('hidden');

            // --- Renderizado de Gráficas Múltiples ---
            const chartsContainer = document.getElementById('previewChartsContainer');
            chartsContainer.innerHTML = '';

            if (data.images && data.images.length > 0) {
                data.images.forEach(imgData => {
                    const box = document.createElement('div');
                    box.className = 'bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex flex-col items-center hover:shadow-md transition';
                    box.innerHTML = `<h4 class="text-sm font-semibold text-slate-800 tracking-wide mb-2">${imgData.target_column}</h4>
                                     <img src="data:image/png;base64,${imgData.base64}" alt="Chart ${imgData.target_column}" class="max-w-full h-auto rounded">`;
                    chartsContainer.appendChild(box);
                });
            }

            // --- Renderizado de Tabla Pivoteada ---
            const thRow = document.getElementById('previewTableHeadRow');
            thRow.innerHTML = '<th class="py-3 px-6 text-slate-800 font-semibold text-sm border-b border-slate-200">Métrica Evaluada</th>';
            if (data.variables) {
                data.variables.forEach(v => {
                    thRow.innerHTML += `<th class="py-3 px-6 text-slate-800 font-semibold text-sm border-b border-slate-200 text-center">${v}</th>`;
                });
            }

            const previewTableBody = document.getElementById('previewTableBody');
            previewTableBody.innerHTML = '';

            for (const [metricName, varsDict] of Object.entries(data.results_pivot)) {
                let formattedMetricName = metricName.replace(/_/g, ' ');
                formattedMetricName = formattedMetricName.charAt(0).toUpperCase() + formattedMetricName.slice(1);

                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50 transition-colors duration-150';

                let rowHtml = `<td class="py-3 px-6 text-sm text-slate-800 font-medium border-b border-slate-100">${formattedMetricName}</td>`;

                if (data.variables) {
                    data.variables.forEach(v => {
                        let cellVal = varsDict[v] !== undefined ? varsDict[v] : 'N/A';
                        rowHtml += `<td class="py-3 px-6 text-sm text-slate-600 border-b border-slate-100 whitespace-pre-wrap font-mono align-top text-center">${cellVal}</td>`;
                    });
                }
                tr.innerHTML = rowHtml;
                previewTableBody.appendChild(tr);
            }

            // Asignar eventos a los botones
            const btnNewAnalysis = document.getElementById('btnNewAnalysis');
            btnNewAnalysis.onclick = () => {
                previewContainer.classList.add('hidden');
                form.classList.remove('hidden');
                form.reset();
                fileDisplayContainer.classList.add('hidden');
                fileInput.value = '';
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Analizar y Generar';
            };

            const btnDownloadExcel = document.getElementById('btnDownloadExcel');
            btnDownloadExcel.onclick = () => {
                window.location.href = '/download/excel/';
            };

            const btnDownloadPdf = document.getElementById('btnDownloadPdf');
            btnDownloadPdf.onclick = () => {
                window.location.href = '/download/pdf/';
            };

        } catch (error) {
            showError(error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Analizar y Generar';
        }
    });

    function showError(msg) {
        errorMessage.textContent = msg;
        errorAlert.classList.remove('hidden');
        // Scroll hasta arriba suavemente
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
