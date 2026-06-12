document.addEventListener('DOMContentLoaded', function () {
    initTabs();
    initAccordionBehavior();
    initDynamicListButtons();
    initFileUploads();
    initAdminFormSubmit();
});

function initTabs() {
    const tabButtons = document.querySelectorAll('[data-tab-target]');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function () {
            const targetId = button.dataset.tabTarget;
            const target = document.getElementById(targetId);

            if (!target) return;

            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            target.classList.add('active');

            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
}

function initAccordionBehavior() {
    const accordions = document.querySelectorAll('.admin-accordion');

    accordions.forEach(details => {
        const indicator = details.querySelector('.accordion-open-indicator');
        if (indicator) {
            indicator.textContent = details.open ? 'סגור' : 'פתח עריכה';
        }

        details.addEventListener('toggle', function () {
            const currentIndicator = details.querySelector('.accordion-open-indicator');

            if (currentIndicator) {
                currentIndicator.textContent = details.open ? 'סגור' : 'פתח עריכה';
            }

            if (details.open) {
                accordions.forEach(other => {
                    if (other !== details) {
                        other.open = false;

                        const otherIndicator = other.querySelector('.accordion-open-indicator');
                        if (otherIndicator) {
                            otherIndicator.textContent = 'פתח עריכה';
                        }
                    }
                });

                setTimeout(() => {
                    details.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 120);
            }
        });
    });
}

function initDynamicListButtons() {
    document.addEventListener('click', function (event) {
        const addButton = event.target.closest('[data-add-item]');
        const deleteButton = event.target.closest('[data-delete-item]');

        if (addButton) {
            const containerId = addButton.dataset.addItem;
            const placeholder = addButton.dataset.placeholder || 'פריט חדש';
            addItem(containerId, placeholder);
            return;
        }

        if (deleteButton) {
            const item = deleteButton.closest('.edit-item');
            if (item) item.remove();
        }
    });
}

function initFileUploads() {
    document.querySelectorAll('[data-upload-list]').forEach(input => {
        input.addEventListener('change', function (event) {
            const containerId = input.dataset.uploadList;
            const statusId = input.dataset.uploadStatus;

            uploadListFile(event, containerId, statusId);
        });
    });
}

function initAdminFormSubmit() {
    const form = document.getElementById('adminForm');

    if (!form) return;

    form.addEventListener('submit', function () {
        prepareData();
    });
}

function setSaveStatus(message, type = 'info') {
    const statusEl = document.getElementById('saveStatus');

    if (!statusEl) return;

    statusEl.textContent = message;
    statusEl.className = 'save-status ' + type;
}

function escapeAttr(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('"', '&quot;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
}

function addItem(containerId, placeholder) {
    const container = document.getElementById(containerId);

    if (!container) return;

    const div = document.createElement('div');
    div.className = 'edit-item';

    div.innerHTML = `
        <div class="edit-item-row">
            <input type="text" value="${escapeAttr(placeholder)}" class="edit-input val-item">
            <button type="button" class="btn-del" data-delete-item>מחק</button>
        </div>
    `;

    container.prepend(div);
}

function collectList(containerId) {
    return Array.from(document.querySelectorAll(`#${containerId} .val-item`))
        .map(input => input.value.trim())
        .filter(value => value !== "");
}

function prepareData() {
    const saveButtons = document.querySelectorAll('#saveTopBtn, #saveBottomBtn');

    saveButtons.forEach(btn => {
        btn.disabled = true;
        btn.textContent = 'שומר...';
    });

    setSaveStatus('שומר שינויים...', 'info');

    const hiddenSpecs = document.getElementById('hidden-specs');
    const hiddenStatuses = document.getElementById('hidden-statuses');
    const hiddenFeedback = document.getElementById('hidden-feedback');

    if (hiddenSpecs) {
        hiddenSpecs.value = collectList('list-specs').join(',');
    }

    if (hiddenStatuses) {
        hiddenStatuses.value = collectList('list-statuses').join(',');
    }

    if (hiddenFeedback) {
        hiddenFeedback.value = collectList('list-feedback').join(',');
    }

    return true;
}

function parseCSVData(text) {
    const cleanText = String(text || '').replace(/^\uFEFF/, '').trim();

    if (!cleanText) return [];

    const lines = cleanText.split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean);

    if (lines.length === 1 && lines[0].includes(',')) {
        return lines[0]
            .split(',')
            .map(item => item.trim().replace(/^"|"$/g, ''))
            .filter(Boolean);
    }

    return lines
        .map(line => {
            if (line.includes(',')) {
                return line.split(',')[0].trim().replace(/^"|"$/g, '');
            }

            return line.replace(/^"|"$/g, '').trim();
        })
        .filter(Boolean);
}

function parseFileData(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = function (event) {
            try {
                const content = event.target.result;
                let data = [];

                if (file.name.endsWith('.json')) {
                    const json = JSON.parse(content);
                    data = Array.isArray(json) ? json : Object.values(json);

                    data = data.map(item => {
                        if (typeof item === 'string') return item;

                        if (item && typeof item === 'object') {
                            return item.name || item.label || item.value || item.שם || '';
                        }

                        return '';
                    });
                } else {
                    data = parseCSVData(content);
                }

                resolve(data.filter(item => item && String(item).trim().length > 0));
            } catch (error) {
                reject(error);
            }
        };

        reader.onerror = reject;
        reader.readAsText(file, 'utf-8');
    });
}

function uploadListFile(event, containerId, statusId) {
    const file = event.target.files[0];

    if (!file) return;

    const statusEl = document.getElementById(statusId);

    if (statusEl) {
        statusEl.textContent = 'בעיבוד...';
    }

    parseFileData(file)
        .then(items => {
            const container = document.getElementById(containerId);

            if (!container) return;

            container.innerHTML = '';

            items.forEach(item => {
                const value = String(item).trim();

                if (!value) return;

                const div = document.createElement('div');
                div.className = 'edit-item';

                div.innerHTML = `
                    <div class="edit-item-row">
                        <input type="text" value="${escapeAttr(value)}" class="edit-input val-item">
                        <button type="button" class="btn-del" data-delete-item>מחק</button>
                    </div>
                `;

                container.appendChild(div);
            });

            if (statusEl) {
                statusEl.textContent = `✅ הועלו ${items.length} פריטים`;

                setTimeout(() => {
                    statusEl.textContent = '';
                }, 3000);
            }

            event.target.value = '';
        })
        .catch(error => {
            console.error(error);

            if (statusEl) {
                statusEl.textContent = '❌ שגיאה בקריאת הקובץ';

                setTimeout(() => {
                    statusEl.textContent = '';
                }, 3000);
            }
        });
}
