// Analysis Form JavaScript
document.addEventListener('DOMContentLoaded', () => {

    // ── METRIC VALIDATION SYSTEM ──────────────────────────────────────────
    let dataProfile = null;
    const activeWarnings = {}; // {metricValue: warningText}

    function validateMetric(val, profile) {
        if (!profile) return null;
        const n = profile.total_rows || 0;
        const hasNeg  = profile.has_negative;
        const hasZero = profile.has_zero;
        const uRatio  = profile.unique_ratio || 0;

        switch (val) {
            case 'media':
                if (n < 1) return '⚠️ Media: no se encontraron datos.';
                break;
            case 'mediana':
                if (n < 1) return '⚠️ Mediana: no se encontraron datos.';
                break;
            case 'moda':
                if (uRatio >= 0.95) return '⚠️ Moda: casi todos los valores son únicos (ratio=' + (uRatio*100).toFixed(0) + '%) — la moda puede no ser representativa.';
                break;
            case 'media_armonica':
                if (hasNeg) return '⚠️ Media Armónica: los datos contienen valores negativos — resultado indefinido.';
                if (hasZero) return '⚠️ Media Armónica: los datos contienen ceros — división por cero.';
                break;
            case 'media_geometrica':
                if (hasNeg) return '⚠️ Media Geométrica: los datos contienen valores negativos — resultado indefinido.';
                if (hasZero) return '⚠️ Media Geométrica: los datos contienen ceros — el producto será cero.';
                break;
            case 'varianza':
                if (n < 2) return '⚠️ Varianza: se necesitan al menos 2 datos (tienes ' + n + ').';
                break;
            case 'desviacion_estandar':
                if (n < 2) return '⚠️ Desviación Estándar: se necesitan al menos 2 datos (tienes ' + n + ').';
                break;
            case 'coeficiente_variacion':
                if (n < 2) return '⚠️ Coef. Variación: se necesitan al menos 2 datos.';
                break;
            case 'media_movil':
                if (n < 3) return '⚠️ Media Móvil: se necesitan al menos 3 datos (ventana mínima).';
                break;
            case 'asimetria':
                if (n < 3) return '⚠️ Asimetría: se necesitan al menos 3 datos (tienes ' + n + ').';
                break;
            case 'curtosis':
                if (n < 4) return '⚠️ Curtosis: se necesitan al menos 4 datos (tienes ' + n + ').';
                break;
            case 'tabla_frecuencias':
                if (n < 2) return '⚠️ Tabla de Frecuencias: se necesitan al menos 2 datos.';
                break;
            default:
                if (val.startsWith('cuartil_')) {
                    if (n < 4)  return '⚠️ Cuartiles: se necesitan al menos 4 datos (tienes ' + n + ').';
                    if (n < 20) return '⚠️ Cuartiles: muestra pequeña (' + n + ' datos) — los cuartiles pueden no ser representativos.';
                } else if (val.startsWith('decil_')) {
                    const d = parseInt(val.split('_')[1]);
                    if (n < 10) return '⚠️ Decil ' + d + ': se necesitan al menos 10 datos (tienes ' + n + ').';
                    if (n < 30) return '⚠️ Decil ' + d + ': muestra pequeña (' + n + ' datos) — los deciles pueden ser imprecisos.';
                } else if (val.startsWith('percentil_')) {
                    const p = parseInt(val.split('_')[1]);
                    const minRec = Math.max(30, p * 2);
                    if (n < p)      return '⚠️ Percentil ' + p + ': datos insuficientes (' + n + ') — se necesitan al menos ' + p + '.';
                    if (n < minRec) return '⚠️ Percentil ' + p + ': muestra insuficiente (' + n + ' datos) — se recomiendan al menos ' + minRec + ' para mayor confiabilidad.';
                }
        }
        return null;
    }

    function updateWarningsPanel() {
        const panel = document.getElementById('metricsWarningsPanel');
        if (!panel) return;
        const entries = Object.entries(activeWarnings);
        if (entries.length === 0) {
            panel.classList.add('hidden');
            panel.innerHTML = '';
            return;
        }
        panel.classList.remove('hidden');
        panel.innerHTML = entries.map(([, msg]) =>
            '<div class="flex items-start gap-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl px-4 py-2.5 text-xs text-amber-800 dark:text-amber-300">' +
            '<svg class="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>' +
            '<span>' + msg + '</span></div>'
        ).join('');
    }

    function attachMetricWarning(checkbox) {
        checkbox.addEventListener('change', function () {
            const val = this.value;
            if (this.checked) {
                const w = validateMetric(val, dataProfile);
                if (w) activeWarnings[val] = w;
            } else {
                delete activeWarnings[val];
            }
            updateWarningsPanel();
        });
    }
    // ─────────────────────────────────────────────────────────────────────

    // Inyección de checkboxes de posición
    function makePositionCheckbox(value, label, container) {
        const lbl = document.createElement('label');
        lbl.className = 'flex items-center hover:bg-slate-50 dark:hover:bg-slate-700/50 p-1 rounded transition-colors cursor-pointer';
        const cb = document.createElement('input');
        cb.type = 'checkbox'; cb.name = 'metrics[]'; cb.value = value;
        cb.className = 'form-checkbox h-4 w-4 text-blue-600 rounded border-slate-300 dark:border-slate-600 focus:ring-blue-500';
        const sp = document.createElement('span');
        sp.className = 'ml-2 text-sm font-medium text-slate-700 dark:text-slate-300';
        sp.textContent = label;
        lbl.appendChild(cb); lbl.appendChild(sp);
        container.appendChild(lbl);
        attachMetricWarning(cb);
    }

    const cContainer = document.querySelector('#cuartilesContainer');
    if (cContainer) {
        for (let i = 1; i <= 4; i++) makePositionCheckbox('cuartil_' + i, 'Cuartil ' + i, cContainer);
    }

    const dContainer = document.querySelector('#decilesContainer .grid');
    if (dContainer) {
        for (let i = 1; i <= 9; i++) makePositionCheckbox('decil_' + i, 'Decil ' + i, dContainer);
    }

    const pContainer = document.querySelector('#percentilesContainer .grid');
    if (pContainer) {
        for (let i = 1; i <= 99; i++) makePositionCheckbox('percentil_' + i, 'Percentil ' + i, pContainer);
    }

    // Attach warning listeners to all STATIC metric checkboxes
    document.querySelectorAll('input[name="metrics[]"]').forEach(cb => attachMetricWarning(cb));

    const form = document.getElementById('analysisForm');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileDisplayContainer = document.getElementById('fileDisplayContainer');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');
    const submitBtn = document.getElementById('submitBtn');

    if (!form || !dropZone || !fileInput || !removeFileBtn || !submitBtn) {
        console.error("DOM no está listo o faltan IDs críticos.");
        return;
    }

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
        if (!list) return;
        const count = list.children.length;
        const btn = document.getElementById('btnAddVariable');
        const msg = document.getElementById('varLimitMsg');

        if (count >= 5) {
            if(btn) {
                btn.disabled = true;
                btn.classList.add('opacity-50', 'cursor-not-allowed');
            }
            if(msg) msg.classList.remove('hidden');
        } else {
            if(btn) {
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
            if(msg) msg.classList.add('hidden');
        }
    }

    function addVariableRow() {
        const list = document.getElementById('variablesList');
        if (!list || list.children.length >= 5) return;

        const row = document.createElement('div');
        row.className = "flex gap-3 items-center row-variable glass-card p-3 rounded-xl shadow-sm";

        let colsOpts = availableColumns.map(c => '<option value="' + c + '">' + c + '</option>').join('');

        row.innerHTML = '' +
            '<select class="var-col form-select flex-1 bg-white/80 dark:bg-slate-700/80 border border-slate-200 dark:border-slate-600 focus:border-blue-500 focus:ring-blue-500 text-slate-700 dark:text-slate-200 rounded-lg transition-shadow text-sm">' +
                colsOpts +
            '</select>' +
            '<select class="var-chart form-select w-40 bg-white/80 dark:bg-slate-700/80 border border-slate-200 dark:border-slate-600 focus:border-blue-500 focus:ring-blue-500 text-slate-700 dark:text-slate-200 rounded-lg transition-shadow text-sm">' +
                '<option value="bar">Columnas</option>' +
                '<option value="line">Lineal</option>' +
                '<option value="pie">Circular</option>' +
                '<option value="scatter">Dispersión</option>' +
                '<option value="frequency">Frecuencias</option>' +
            '</select>' +
            '<button type="button" class="btn-remove-var text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/30 p-2 rounded-lg transition-colors">' +
                '<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>' +
            '</button>';

        row.querySelector('.btn-remove-var').addEventListener('click', () => {
            row.remove();
            updateVarLimit();
        });

        list.appendChild(row);
        updateVarLimit();
    }

    const btnAddVariable = document.getElementById('btnAddVariable');
    if (btnAddVariable) {
        btnAddVariable.addEventListener('click', addVariableRow);
    }

    let allSheetsData = [];

    async function fetchColumnsForFiles(files) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput) return;
        const csrftoken = csrfInput.value;
        const columnSelectionContainer = document.getElementById('variableBuilderContainer');
        const previewContainer = document.getElementById('dataPreviewContainer');

        try {
            const resp = await fetch('/api/columns/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrftoken },
                body: formData
            });

            if (resp.ok) {
                const data = await resp.json();

                // Store global data profile for metric validation
                if (data.data_profile) {
                    dataProfile = data.data_profile;
                    // Re-clear any stale warnings when a new file is loaded
                    Object.keys(activeWarnings).forEach(k => delete activeWarnings[k]);
                    updateWarningsPanel();
                    // Re-validate any already-checked metrics against the new profile
                    document.querySelectorAll('input[name="metrics[]"]:checked').forEach(cb => {
                        const w = validateMetric(cb.value, dataProfile);
                        if (w) activeWarnings[cb.value] = w;
                    });
                    updateWarningsPanel();
                }
                if (data.sheets && data.sheets.length > 0) {
                    allSheetsData = data.sheets;
                    
                    // Mezclar todas las columnas únicas para el selector de variables
                    let uniqueCols = new Set();
                    allSheetsData.forEach(sheet => {
                        sheet.columns.forEach(c => uniqueCols.add(c));
                    });
                    availableColumns = Array.from(uniqueCols);
                    
                    const vList = document.getElementById('variablesList');
                    if (vList) vList.innerHTML = '';
                    addVariableRow();
                    if (columnSelectionContainer) columnSelectionContainer.classList.remove('hidden');
                    
                    if (previewContainer) {
                        try {
                            const selector = document.getElementById('previewSelector');
                            if (selector) {
                                selector.innerHTML = '';
                                if (allSheetsData.length > 1) {
                                    allSheetsData.forEach((sheet, idx) => {
                                        selector.innerHTML += `<option value="${idx}">${sheet.name}</option>`;
                                    });
                                    selector.classList.remove('hidden');
                                    selector.onchange = (e) => renderPreviewSheet(allSheetsData[e.target.value]);
                                } else {
                                    selector.classList.add('hidden');
                                }
                            }
                            renderPreviewSheet(allSheetsData[0]);
                            previewContainer.classList.remove('hidden');
                        } catch (e) {
                            console.error("Preview render error:", e);
                        }
                    }
                }
            } else {
                console.error("Error API:", await resp.json());
            }
        } catch (e) {
            console.error("Error fetching columns", e);
        }
    }

    function renderPreviewSheet(sheetData) {
        const thead = document.getElementById('dataPreviewHead');
        const tbody = document.getElementById('dataPreviewBody');
        if (thead && tbody && sheetData) {
            let headHtml = '<tr>';
            sheetData.columns.forEach(col => {
                headHtml += '<th class="px-4 py-3 font-medium tracking-wider text-slate-600 dark:text-slate-400">' + col + '</th>';
            });
            headHtml += '</tr>';
            thead.innerHTML = headHtml;
            
            let bodyHtml = '';
            sheetData.preview.forEach(row => {
                bodyHtml += '<tr>';
                sheetData.columns.forEach(col => {
                    bodyHtml += '<td class="px-4 py-3 whitespace-nowrap text-slate-700 dark:text-slate-300">' + (row[col] !== null && row[col] !== undefined ? row[col] : '-') + '</td>';
                });
                bodyHtml += '</tr>';
            });
            tbody.innerHTML = bodyHtml;
        }
    }

    function showFileName() {
        if (fileInput.files.length > 0) {
            if (fileNameDisplay) {
                fileNameDisplay.innerHTML = '';
                for (let i = 0; i < fileInput.files.length; i++) {
                    fileNameDisplay.innerHTML += `<span class="inline-block bg-white/70 dark:bg-slate-700/70 border border-violet-200 dark:border-violet-800 text-violet-700 dark:text-violet-300 px-3 py-1 rounded-full text-xs font-semibold mr-2 mt-2 shadow-sm text-center">📦 ${fileInput.files[i].name}</span>`;
                }
            }
            if (fileDisplayContainer) fileDisplayContainer.classList.remove('hidden');
            fetchColumnsForFiles(fileInput.files);
        } else {
            if (fileDisplayContainer) fileDisplayContainer.classList.add('hidden');
            const colContainer = document.getElementById('variableBuilderContainer');
            if (colContainer) colContainer.classList.add('hidden');
            const previewContainer = document.getElementById('dataPreviewContainer');
            if (previewContainer) previewContainer.classList.add('hidden');
        }
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.value = '';
            const vList = document.getElementById('variablesList');
            if (vList) vList.innerHTML = '';
            showFileName();
            if (errorAlert) errorAlert.classList.add('hidden');
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (errorAlert) errorAlert.classList.add('hidden');

        if (!fileInput.files.length) {
            showError("Por favor selecciona un documento para iniciar el análisis.");
            return;
        }

        const checkedBoxOptions = document.querySelectorAll('input[name="metrics[]"]:checked');
        if (checkedBoxOptions.length === 0) {
            showError("Debes seleccionar al menos una métrica a calcular.");
            return;
        }

        const formData = new FormData();
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('file', fileInput.files[i]);
        }

        checkedBoxOptions.forEach(checkbox => {
            formData.append('metrics[]', checkbox.value);
        });

        const formatSelect = document.querySelector('input[name="format"]:checked');
        const format = formatSelect ? formatSelect.value : 'excel';
        formData.append('format', format);

        const layoutSelect = document.querySelector('input[name="layout"]:checked');
        const layout = layoutSelect ? layoutSelect.value : 'horizontal';
        formData.append('layout', layout);

        const detailLevel = document.getElementById('detailLevel');
        if (detailLevel) {
            formData.append('detail_level', detailLevel.value);
        }

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
        submitBtn.innerHTML = '<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Procesando...';

        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput) { showError("CSRF token no encontrado"); return; }
        
        try {
            const response = await fetch('/analysis/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfInput.value },
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Error interno del servidor Django.');
            }

            const data = await response.json();

            form.classList.add('hidden');
            const previewContainer = document.getElementById('previewContainer');
            if (previewContainer) previewContainer.classList.remove('hidden');

            const chartsContainer = document.getElementById('previewChartsContainer');
            if (chartsContainer) {
                chartsContainer.innerHTML = '';
                if (data.images && data.images.length > 0) {
                    data.images.forEach(imgData => {
                        const box = document.createElement('div');
                        box.className = 'glass-card p-3 rounded-xl flex flex-col items-center hover:shadow-md transition';
                        box.innerHTML = '<h4 class="text-sm font-semibold text-slate-800 dark:text-slate-200 tracking-wide mb-2">' + imgData.target_column + '</h4><img src="data:image/png;base64,' + imgData.base64 + '" alt="Chart ' + imgData.target_column + '" class="max-w-full h-auto rounded">';
                        chartsContainer.appendChild(box);
                    });
                }
            }

            const thRow = document.getElementById('previewTableHeadRow');
            if (thRow) {
                thRow.innerHTML = '<th class="py-3 px-6 text-slate-800 dark:text-slate-200 font-semibold text-sm border-b border-slate-200 dark:border-slate-700">Métrica Evaluada</th>';
                if (data.variables) {
                    data.variables.forEach(v => {
                        thRow.innerHTML += '<th class="py-3 px-6 text-slate-800 dark:text-slate-200 font-semibold text-sm border-b border-slate-200 dark:border-slate-700 text-center">' + v + '</th>';
                    });
                }
            }

            const previewTableBody = document.getElementById('previewTableBody');
            if (previewTableBody) {
                previewTableBody.innerHTML = '';
                for (const [metricName, varsDict] of Object.entries(data.results_pivot)) {
                    let formattedMetricName = metricName.replace(/_/g, ' ');
                    formattedMetricName = formattedMetricName.charAt(0).toUpperCase() + formattedMetricName.slice(1);

                    const firstVal = typeof varsDict === 'object' ? Object.values(varsDict)[0] : null;
                    if (firstVal !== null && typeof firstVal === 'object' && !Array.isArray(firstVal)) {
                        const subKeys = new Set();
                        Object.values(varsDict).forEach(subDict => {
                            if (typeof subDict === 'object') Object.keys(subDict).forEach(k => subKeys.add(k));
                        });
                        subKeys.forEach(sk => {
                            const tr = document.createElement('tr');
                            tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors duration-150';
                            let rowHtml = '<td class="py-3 px-6 text-sm text-slate-800 dark:text-slate-200 font-medium border-b border-slate-100 dark:border-slate-700">' + formattedMetricName + ' – ' + sk + '</td>';
                            if (data.variables) {
                                data.variables.forEach(v => {
                                    let subDict = varsDict[v];
                                    let cellVal = (subDict && subDict[sk] !== undefined) ? subDict[sk] : 'N/A';
                                    rowHtml += '<td class="py-3 px-6 text-sm text-slate-600 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700 whitespace-pre-wrap font-mono align-top text-center">' + cellVal + '</td>';
                                });
                            }
                            tr.innerHTML = rowHtml;
                            previewTableBody.appendChild(tr);
                        });
                    } else {
                        const tr = document.createElement('tr');
                        tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors duration-150';
                        let rowHtml = '<td class="py-3 px-6 text-sm text-slate-800 dark:text-slate-200 font-medium border-b border-slate-100 dark:border-slate-700">' + formattedMetricName + '</td>';
                        if (data.variables) {
                            data.variables.forEach(v => {
                                let cellVal = varsDict[v] !== undefined ? varsDict[v] : 'N/A';
                                if (typeof cellVal === 'object' && cellVal !== null) {
                                    cellVal = Object.entries(cellVal).map(([k, vv]) => k + ': ' + vv).join('\n');
                                }
                                rowHtml += '<td class="py-3 px-6 text-sm text-slate-600 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700 whitespace-pre-wrap font-mono align-top text-center">' + cellVal + '</td>';
                            });
                        }
                        tr.innerHTML = rowHtml;
                        previewTableBody.appendChild(tr);
                    }
                }
            }

            // Renderizar Tablas de Distribución de Frecuencias
            if (data.freq_tables && Object.keys(data.freq_tables).length > 0) {
                const previewContainer2 = document.getElementById('previewContainer');
                let ftSection = document.getElementById('freqTablesSection');
                if (!ftSection) {
                    ftSection = document.createElement('div');
                    ftSection.id = 'freqTablesSection';
                    ftSection.className = 'mt-8';
                    const actionsBar = previewContainer2.querySelector('.flex.flex-col.sm\\:flex-row');
                    if (actionsBar) {
                        actionsBar.parentElement.insertBefore(ftSection, actionsBar);
                    } else {
                        previewContainer2.querySelector('.glass, .dark\\:bg-slate-800')?.appendChild(ftSection);
                    }
                }
                ftSection.innerHTML = '';

                const ftTitle = document.createElement('h3');
                ftTitle.className = 'text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 border-b border-slate-100 dark:border-slate-700 pb-2';
                ftTitle.textContent = 'Tablas de Distribución de Frecuencias';
                ftSection.appendChild(ftTitle);

                for (const [varName, ftData] of Object.entries(data.freq_tables)) {
                    const varBlock = document.createElement('div');
                    varBlock.className = 'mb-6';

                    const varTitle = document.createElement('h4');
                    varTitle.className = 'text-sm font-semibold text-blue-600 dark:text-blue-400 mb-1';
                    varTitle.textContent = 'Variable: ' + varName;
                    varBlock.appendChild(varTitle);

                    const infoP = document.createElement('p');
                    infoP.className = 'text-xs text-slate-500 dark:text-slate-400 mb-3';
                    infoP.textContent = 'n = ' + ftData.n + ' | k (clases) = ' + ftData.k + ' | Rango = ' + ftData.rango + ' | Amplitud = ' + ftData.amplitud;
                    varBlock.appendChild(infoP);

                    const tableWrapper = document.createElement('div');
                    tableWrapper.className = 'overflow-x-auto glass-card rounded-xl shadow-sm';

                    let tableHtml = '<table class="w-full text-left border-collapse">';
                    tableHtml += '<thead class="bg-blue-50 dark:bg-blue-900/30 border-b border-slate-200 dark:border-slate-700">';
                    tableHtml += '<tr>';
                    ['Intervalo', 'Marca (xi)', 'fi', 'Fi', 'hi', 'Hi'].forEach(h => {
                        tableHtml += '<th class="py-2.5 px-4 text-slate-700 dark:text-slate-300 font-semibold text-xs uppercase tracking-wider text-center">' + h + '</th>';
                    });
                    tableHtml += '</tr></thead><tbody class="divide-y divide-slate-100 dark:divide-slate-700">';

                    ftData.filas.forEach((fila, idx) => {
                        const bgClass = idx % 2 === 0 ? '' : 'bg-slate-50/50 dark:bg-slate-800/30';
                        tableHtml += '<tr class="' + bgClass + ' hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">';
                        tableHtml += '<td class="py-2 px-4 text-sm text-slate-700 dark:text-slate-300 font-mono text-center">' + fila.intervalo + '</td>';
                        tableHtml += '<td class="py-2 px-4 text-sm text-slate-600 dark:text-slate-400 font-mono text-center">' + fila.xi + '</td>';
                        tableHtml += '<td class="py-2 px-4 text-sm text-slate-600 dark:text-slate-400 font-mono text-center font-semibold">' + fila.fi + '</td>';
                        tableHtml += '<td class="py-2 px-4 text-sm text-slate-600 dark:text-slate-400 font-mono text-center">' + fila.Fi + '</td>';
                        tableHtml += '<td class="py-2 px-4 text-sm text-slate-600 dark:text-slate-400 font-mono text-center">' + fila.hi + '</td>';
                        tableHtml += '<td class="py-2 px-4 text-sm text-slate-600 dark:text-slate-400 font-mono text-center">' + fila.Hi + '</td>';
                        tableHtml += '</tr>';
                    });

                    tableHtml += '</tbody></table>';
                    tableWrapper.innerHTML = tableHtml;
                    varBlock.appendChild(tableWrapper);
                    ftSection.appendChild(varBlock);
                }
            }

            const btnNewAnalysis = document.getElementById('btnNewAnalysis');
            if (btnNewAnalysis) {
                btnNewAnalysis.onclick = () => {
                    if (previewContainer) previewContainer.classList.add('hidden');
                    form.classList.remove('hidden');

                    fileInput.value = '';
                    if (fileDisplayContainer) fileDisplayContainer.classList.add('hidden');
                    if (fileNameDisplay) fileNameDisplay.innerHTML = '';

                    const dataPreviewContainer = document.getElementById('dataPreviewContainer');
                    if (dataPreviewContainer) dataPreviewContainer.classList.add('hidden');
                    const selector = document.getElementById('previewSelector');
                    if (selector) { selector.innerHTML = ''; selector.classList.add('hidden'); }
                    allSheetsData = [];
                    availableColumns = [];

                    const vList = document.getElementById('variablesList');
                    if (vList) vList.innerHTML = '';
                    const varBuilderContainer = document.getElementById('variableBuilderContainer');
                    if (varBuilderContainer) varBuilderContainer.classList.add('hidden');

                    document.querySelectorAll('input[name="metrics[]"]').forEach(cb => cb.checked = false);
                    const selectAll = document.getElementById('selectAllMetrics');
                    if (selectAll) selectAll.checked = false;

                    submitBtn.disabled = false;
                    submitBtn.innerHTML = 'Analizar y Generar Documento';

                    window.scrollTo({ top: 0, behavior: 'smooth' });
                };
            }

            const btnDownloadExcel = document.getElementById('btnDownloadExcel');
            if (btnDownloadExcel) btnDownloadExcel.onclick = () => { window.location.href = '/download/excel/'; };

            const btnDownloadPdf = document.getElementById('btnDownloadPdf');
            if (btnDownloadPdf) btnDownloadPdf.onclick = () => { window.location.href = '/download/pdf/'; };

        } catch (error) {
            showError(error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Analizar y Generar Documento';
        }
    });

    function showError(msg) {
        if (errorMessage) errorMessage.textContent = msg;
        if (errorAlert) errorAlert.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

}); // Fin DOMContentLoaded
