document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form[data-strip-empty-fields='1']");
    if (!form) {
        return;
    }

    form.addEventListener("submit", function () {
        const inputs = form.querySelectorAll("input[type='text']");
        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.removeAttribute("name");
            }
        });
    });
});
