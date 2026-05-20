/**
 * Biblioteca de documentos .txt (SQLite) — selector multi-artículo compartido.
 */
(function (global) {
    const ACCENT_MAP = {
        purple: { ring: 'ring-purple-500', bg: 'bg-purple-600', border: 'border-purple-500/40', text: 'text-purple-600 dark:text-purple-400' },
        cyan: { ring: 'ring-cyan-500', bg: 'bg-cyan-600', border: 'border-cyan-500/40', text: 'text-cyan-600 dark:text-cyan-400' },
        pink: { ring: 'ring-pink-500', bg: 'bg-pink-600', border: 'border-pink-500/40', text: 'text-pink-600 dark:text-pink-400' },
    };

    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input && input.value) return input.value;
        const m = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[2]) : null;
    }

    class DocumentLibrary {
        constructor(rootEl) {
            this.root = rootEl;
            this.accent = rootEl.dataset.accent || 'cyan';
            this.listEl = rootEl.querySelector('[data-doc-list]');
            this.emptyEl = rootEl.querySelector('[data-doc-empty]');
            this.countEl = rootEl.querySelector('[data-doc-count]');
            this.uploadInput = rootEl.querySelector('[data-doc-upload-input]');
            this.uploadBtn = rootEl.querySelector('[data-doc-upload-btn]');
            this.selectAllBtn = rootEl.querySelector('[data-doc-select-all]');
            this.clearBtn = rootEl.querySelector('[data-doc-clear]');
            this.onSelectionChange = null;
            this.documents = [];
            this._bind();
            this.refresh();
        }

        _bind() {
            if (this.uploadBtn && this.uploadInput) {
                this.uploadBtn.addEventListener('click', () => this.uploadInput.click());
                this.uploadInput.addEventListener('change', () => this._handleUpload());
            }
            if (this.selectAllBtn) {
                this.selectAllBtn.addEventListener('click', () => {
                    this.root.querySelectorAll('[data-doc-checkbox]').forEach(cb => { cb.checked = true; });
                    this._notify();
                });
            }
            if (this.clearBtn) {
                this.clearBtn.addEventListener('click', () => {
                    this.root.querySelectorAll('[data-doc-checkbox]').forEach(cb => { cb.checked = false; });
                    this._notify();
                });
            }
        }

        async refresh() {
            try {
                const resp = await fetch('/api/documentos/');
                if (!resp.ok) throw new Error('No se pudo cargar la biblioteca');
                const data = await resp.json();
                this.documents = data.documents || [];
                this._renderList();
            } catch (e) {
                if (this.listEl) this.listEl.innerHTML = `<p class="text-xs text-red-500">${e.message}</p>`;
            }
        }

        _renderList() {
            if (!this.listEl) return;
            this.listEl.innerHTML = '';
            const accent = ACCENT_MAP[this.accent] || ACCENT_MAP.cyan;

            if (this.countEl) {
                this.countEl.textContent = `${this.documents.length} artículo(s) en biblioteca`;
            }
            if (this.emptyEl) {
                this.emptyEl.classList.toggle('hidden', this.documents.length > 0);
            }
            if (!this.documents.length) return;

            this.documents.forEach(doc => {
                const row = document.createElement('label');
                row.className = `flex items-start gap-2 p-2.5 rounded-xl border ${accent.border} bg-white/40 dark:bg-slate-900/40 hover:bg-white/60 dark:hover:bg-slate-800/60 cursor-pointer transition`;
                row.innerHTML = `
                    <input type="checkbox" data-doc-checkbox value="${doc.id}" class="mt-1 rounded ${accent.text} focus:${accent.ring}">
                    <span class="flex-1 min-w-0">
                        <span class="block text-xs font-bold text-slate-800 dark:text-slate-200 truncate">${doc.titulo}</span>
                        <span class="block text-[10px] text-slate-500 truncate">${doc.preview}</span>
                        <span class="block text-[9px] text-slate-400 mt-0.5">${new Date(doc.fecha_subida).toLocaleString()} · ${doc.chars} caracteres</span>
                    </span>
                    <button type="button" data-doc-delete="${doc.id}" class="text-[10px] text-red-500 hover:text-red-400 font-bold px-1" title="Eliminar">×</button>
                `;
                row.querySelector('[data-doc-checkbox]').addEventListener('change', () => this._notify());
                row.querySelector('[data-doc-delete]').addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this._deleteDocument(doc.id);
                });
                this.listEl.appendChild(row);
            });
        }

        getSelectedIds() {
            return Array.from(this.root.querySelectorAll('[data-doc-checkbox]:checked'))
                .map(cb => parseInt(cb.value, 10))
                .filter(id => !isNaN(id));
        }

        appendIdsToFormData(formData) {
            this.getSelectedIds().forEach(id => formData.append('documento_ids[]', id));
        }

        /** POST /api/columns/ con los IDs seleccionados (corpus unificado). */
        async fetchCorpusPreview() {
            const ids = this.getSelectedIds();
            if (!ids.length) return null;
            const csrf = getCsrfToken();
            if (!csrf) throw new Error('Token CSRF no disponible');
            const fd = new FormData();
            this.appendIdsToFormData(fd);
            const resp = await fetch('/api/columns/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf },
                body: fd,
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'No se pudo cargar el corpus');
            return data;
        }

        /** POST /api/bayesian/keywords/ con los IDs seleccionados. */
        async fetchBayesianKeywords() {
            const ids = this.getSelectedIds();
            if (!ids.length) return [];
            const csrf = getCsrfToken();
            if (!csrf) throw new Error('Token CSRF no disponible');
            const fd = new FormData();
            this.appendIdsToFormData(fd);
            const resp = await fetch('/api/bayesian/keywords/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf },
                body: fd,
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'No se pudieron extraer palabras clave');
            return data.keywords || [];
        }

        _notify() {
            if (typeof this.onSelectionChange === 'function') {
                this.onSelectionChange(this.getSelectedIds());
            }
        }

        async _handleUpload() {
            const files = this.uploadInput.files;
            if (!files.length) return;
            const csrf = getCsrfToken();
            if (!csrf) return;

            const fd = new FormData();
            for (const f of files) fd.append('files', f);

            this.uploadBtn.disabled = true;
            this.uploadBtn.textContent = 'Guardando…';
            try {
                const resp = await fetch('/api/documentos/upload/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrf },
                    body: fd,
                });
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || 'Error al guardar');
                this.uploadInput.value = '';
                await this.refresh();
                this.root.querySelectorAll('[data-doc-checkbox]').forEach(cb => {
                    const id = parseInt(cb.value, 10);
                    if (data.saved && data.saved.some(s => s.id === id)) cb.checked = true;
                });
                this._notify();
            } catch (e) {
                alert(e.message);
            } finally {
                this.uploadBtn.disabled = false;
                this.uploadBtn.textContent = 'Guardar .txt en biblioteca';
            }
        }

        async _deleteDocument(id) {
            if (!confirm('¿Eliminar este documento de la biblioteca?')) return;
            const csrf = getCsrfToken();
            const resp = await fetch(`/api/documentos/${id}/delete/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf },
            });
            const data = await resp.json();
            if (resp.ok) await this.refresh();
            else alert(data.error || 'No se pudo eliminar');
        }
    }

    function initAll() {
        document.querySelectorAll('[data-document-library]').forEach(el => {
            if (el._docLib) return;
            el._docLib = new DocumentLibrary(el);
        });
    }

    global.DocumentLibrary = DocumentLibrary;
    global.initDocumentLibraries = initAll;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
})(window);
