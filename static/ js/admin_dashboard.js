function switchTab(tabId, event) {
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.remove('active');
    });

    document.querySelectorAll('.modern-tab').forEach(el => {
        el.classList.remove('active');
        el.classList.add('inactive');
    });

    const target = document.getElementById(tabId);

    if (target) {
        target.classList.add('active');
    }

    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
        event.currentTarget.classList.remove('inactive');
    }

    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

function setSaveStatus(message, type = 'info') {
    const statusEl = document.getElementById('saveStatus');

    if (!statusEl) return;

    statusEl.textContent = message;
    statusEl.className = 'save-status ' + type;
}

function escapeAttr(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('"', '&quot;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
}

function addItem(containerId, placeholder) {
    const container = document.getElementById(containerId);

    if (!container) return;

    const div = document.createElement('div');

    div.className = 'edit-item compact-edit-item';

    div.innerHTML = `
        <div class="edit-item-row compact-edit-row">
            <input
                type="text"
                value="${escapeAttr(placeholder)}"
                class="edit-input val-item"
            >

            <button
                type="button"
                class="btn-delete-pink"
                data-action="delete-edit-item"
            >
                מחק
            </button>
        </div>
    `;

    container.prepend(div);
}

function prepareData(event) {
    const saveButtons = document.querySelectorAll('#saveTopBtn, #saveBottomBtn');

    saveButtons.forEach(btn => {
        btn.disabled = true;
        btn.textContent = 'שומר...';
    });

    setSaveStatus('שומר שינויים...', 'info');

    const specs = Array.from(document.querySelectorAll('#list-specs .val-item'))
        .map(input => input.value.trim())
        .filter(value => value !== '')
        .join(',');

    const statuses = Array.from(document.querySelectorAll('#list-statuses .val-item'))
        .map(input => input.value.trim())
        .filter(value => value !== '')
        .join(',');

    const feedback = Array.from(document.querySelectorAll('#list-feedback .val-item'))
        .map(input => input.value.trim())
        .filter(value => value !== '')
        .join(',');

    const hiddenSpecs = document.getElementById('hidden-specs');
    const hiddenStatuses = document.getElementById('hidden-statuses');
    const hiddenFeedback = document.getElementById('hidden-feedback');

    if (hiddenSpecs) hiddenSpecs.value = specs;
    if (hiddenStatuses) hiddenStatuses.value = statuses;
    if (hiddenFeedback) hiddenFeedback.value = feedback;

    return true;
}

function parseCSVData(text) {
    const cleanText = String(text || '')
        .replace(/^\uFEFF/, '')
        .trim();

    if (!cleanText) return [];

    const lines = cleanText
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => line.length > 0 && !line.startsWith('#'));

    if (lines.length === 1 && lines[0].includes(',')) {
        return lines[0]
            .split(',')
            .map(item => item.trim().replace(/^"|"$/g, ''))
            .filter(Boolean);
    }

    return lines
        .map(line => line.replace(/^"|"$/g, '').trim())
        .filter(Boolean);
}

function parseFileData(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = event => {
            try {
                const content = event.target.result;
                let data = [];

                if (file.name.toLowerCase().endsWith('.json')) {
                    const json = JSON.parse(content);

                    if (Array.isArray(json)) {
                        data = json;
                    } else {
                        data = Object.values(json);
                    }
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

function extractValueFromItem(item) {
    if (typeof item === 'string') {
        return item.trim();
    }

    if (typeof item === 'object' && item !== null) {
        return String(
            item.name ||
            item.label ||
            item.value ||
            item.שם ||
            item["שם"] ||
            item["תחום"] ||
            item["תחום התמחות"] ||
            item["סטטוס"] ||
            item["נקודה"] ||
            item["חוות דעת"] ||
            ''
        ).trim();
    }

    return '';
}

function setUploadStatus(statusId, message, type = 'info') {
    const statusEl = document.getElementById(statusId);

    if (!statusEl) return;

    statusEl.textContent = message;
    statusEl.className = 'upload-status ' + type;
}

function resetUploadStatus(statusId) {
    setTimeout(() => {
        const statusEl = document.getElementById(statusId);

        if (!statusEl) return;

        statusEl.textContent = '';
        statusEl.className = 'upload-status';
    }, 3500);
}

function uploadListFile(file, containerId, statusId) {
    if (!file) return;

    setUploadStatus(statusId, 'בעיבוד...', 'info');

    parseFileData(file)
        .then(items => {
            const container = document.getElementById(containerId);

            if (!container) return;

            container.innerHTML = '';

            items.forEach(item => {
                const value = extractValueFromItem(item);

                if (!value) return;

                const div = document.createElement('div');

                div.className = 'edit-item compact-edit-item';

                div.innerHTML = `
                    <div class="edit-item-row compact-edit-row">
                        <input
                            type="text"
                            value="${escapeAttr(value)}"
                            class="edit-input val-item"
                        >

                        <button
                            type="button"
                            class="btn-delete-pink"
                            data-action="delete-edit-item"
                        >
                            מחק
                        </button>
                    </div>
                `;

                container.appendChild(div);
            });

            setUploadStatus(statusId, `✅ הועלו ${container.children.length} פריטים`, 'success');
            resetUploadStatus(statusId);
        })
        .catch(error => {
            console.error(error);
            setUploadStatus(statusId, '❌ שגיאה בקריאת הקובץ', 'error');
            resetUploadStatus(statusId);
        });
}

function setupDropZones() {
    document.querySelectorAll('.drop-zone').forEach(zone => {
        const containerId = zone.dataset.dropList;
        const statusId = zone.dataset.dropStatus;
        const inputId = zone.dataset.dropInput;
        const input = document.getElementById(inputId);

        if (!containerId || !statusId || !input) return;

        zone.addEventListener('click', event => {
            if (event.target.closest('input')) return;
            input.click();
        });

        zone.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                input.click();
            }
        });

        zone.addEventListener('dragenter', event => {
            event.preventDefault();
            event.stopPropagation();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragover', event => {
            event.preventDefault();
            event.stopPropagation();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', event => {
            event.preventDefault();
            event.stopPropagation();

            if (!zone.contains(event.relatedTarget)) {
                zone.classList.remove('drag-over');
            }
        });

        zone.addEventListener('drop', event => {
            event.preventDefault();
            event.stopPropagation();

            zone.classList.remove('drag-over');

            const file = event.dataTransfer.files && event.dataTransfer.files[0];

            if (!file) return;

            uploadListFile(file, containerId, statusId);
        });

        input.addEventListener('change', () => {
            const file = input.files && input.files[0];

            if (!file) return;

            uploadListFile(file, containerId, statusId);
            input.value = '';
        });
    });
}

function setupAccordionBehavior() {
    const accordions = document.querySelectorAll('.admin-accordion');

    accordions.forEach(details => {
        const indicator = details.querySelector('.accordion-open-indicator');

        if (indicator) {
            indicator.textContent = details.open ? 'סגור' : 'פתח עריכה';
        }

        details.addEventListener('toggle', () => {
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
                    details.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }, 120);
            }
        });
    });
}

function bindAdminEvents() {
    document.addEventListener('click', event => {
        const tabButton = event.target.closest('[data-tab-target]');

        if (tabButton) {
            switchTab(tabButton.dataset.tabTarget, event);
            return;
        }

        const addButton = event.target.closest('[data-action="add-item"]');

        if (addButton) {
            addItem(
                addButton.dataset.targetList,
                addButton.dataset.placeholder || 'פריט חדש'
            );
            return;
        }

        const deleteButton = event.target.closest('[data-action="delete-edit-item"]');

        if (deleteButton) {
            const item = deleteButton.closest('.edit-item');

            if (item) {
                item.remove();
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupAccordionBehavior();
    setupDropZones();
    bindAdminEvents();
});
