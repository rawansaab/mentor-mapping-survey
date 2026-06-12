document.addEventListener('DOMContentLoaded', function () {
    initAllTagMultiselects();
    initFormValidation();
});

function initAllTagMultiselects() {
    document.querySelectorAll('.tag-ms').forEach(initTagMS);
}

function initTagMS(ms) {
    const control = ms.querySelector('.control');
    const menu = ms.querySelector('.menu');
    const chipsBox = ms.querySelector('[data-ms-chips]');
    const placeholder = ms.querySelector('.placeholder');
    const hiddenSelect = ms.querySelector('select[multiple][hidden]');

    if (!control || !menu || !chipsBox || !placeholder || !hiddenSelect) return;

    function updatePlaceholder() {
        placeholder.style.display = hiddenSelect.selectedOptions.length > 0 ? 'none' : 'block';
    }

    function renderChips() {
        chipsBox.innerHTML = '';

        Array.from(hiddenSelect.selectedOptions).forEach(opt => {
            const chip = document.createElement('div');
            chip.className = 'chip';
            chip.dataset.value = opt.value;

            const chipText = document.createElement('span');
            chipText.textContent = opt.value;

            const removeButton = document.createElement('button');
            removeButton.type = 'button';
            removeButton.innerHTML = '&times;';

            removeButton.addEventListener('click', e => {
                e.stopPropagation();
                setSelected(opt.value, false);
            });

            chip.appendChild(chipText);
            chip.appendChild(removeButton);
            chipsBox.appendChild(chip);
        });

        updatePlaceholder();
    }

    function syncMenu() {
        const selected = new Set(
            Array.from(hiddenSelect.selectedOptions).map(option => option.value)
        );

        menu.querySelectorAll('.item').forEach(item => {
            item.classList.toggle('active', selected.has(item.dataset.value));
        });
    }

    function setSelected(value, on) {
        const opt = Array.from(hiddenSelect.options).find(option => option.value === value);
        if (!opt) return;

        opt.selected = !!on;
        renderChips();
        syncMenu();
    }

    control.addEventListener('click', () => {
        ms.classList.toggle('open');
    });

    menu.querySelectorAll('.item').forEach(item => {
        item.addEventListener('click', e => {
            e.stopPropagation();

            const value = item.dataset.value;
            const opt = Array.from(hiddenSelect.options).find(option => option.value === value);

            setSelected(value, !(opt && opt.selected));
        });
    });

    document.addEventListener('click', e => {
        if (!ms.contains(e.target)) {
            ms.classList.remove('open');
        }
    });

    renderChips();
    syncMenu();
}

function initFormValidation() {
    const form = document.getElementById('mentor-form');
    const errorBox = document.getElementById('validation-error-box');
    const errorText = document.getElementById('error-text');
    const fixButton = document.getElementById('fix-error-btn');

    if (!form || !errorBox || !errorText || !fixButton) return;

    let targetErrorElement = null;

    fixButton.addEventListener('click', () => {
        if (targetErrorElement) {
            targetErrorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

            if (typeof targetErrorElement.focus === 'function') {
                targetErrorElement.focus();
            }
        }
    });

    form.addEventListener('submit', function (e) {
        errorBox.style.display = 'none';
        targetErrorElement = null;

        const phoneInput = document.getElementById('phone-input');
        const emailInput = document.getElementById('email-input');
        const feedbackSelect = document.getElementById('feedback-select');

        if (phoneInput) {
            const phone = phoneInput.value.replace(/[-\s]/g, "");

            if (phone && !/^(0?5\d{8})$/.test(phone)) {
                e.preventDefault();

                errorText.innerText = "מספר הטלפון שהוזן אינו תקין. יש להזין מספר נייד (לדוגמה: 0501234567).";
                targetErrorElement = phoneInput;

                showValidationError(errorBox, targetErrorElement);
                return;
            }
        }

        if (emailInput) {
            const email = emailInput.value;

            if (email && !/^[^@]+@[^@]+\.[^@]+$/.test(email)) {
                e.preventDefault();

                errorText.innerText = "כתובת הדוא״ל שהוזנה אינה תקינה.";
                targetErrorElement = emailInput;

                showValidationError(errorBox, targetErrorElement);
                return;
            }
        }

        if (feedbackSelect && feedbackSelect.selectedOptions.length === 0) {
            e.preventDefault();

            errorText.innerText = "חובה לבחור לפחות נקודה אחת בחוות הדעת על המדריך.";
            targetErrorElement = document.querySelector('.tag-ms .control');

            showValidationError(errorBox, targetErrorElement);
        }
    });
}

function showValidationError(errorBox, targetErrorElement) {
    errorBox.style.display = 'block';

    if (targetErrorElement) {
        targetErrorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}
