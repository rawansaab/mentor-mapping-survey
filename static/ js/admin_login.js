function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    if (!input) return;

    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = 'הסתר';
    } else {
        input.type = 'password';
        button.textContent = 'הצג';
    }
}

function handleAdminLoginSubmit(form) {
    const button = form.querySelector('#loginSubmitBtn');

    if (button) {
        button.disabled = true;
        button.textContent = 'טוען...';
    }

    return true;
}
