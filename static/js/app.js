document.documentElement.classList.add("js");

document.querySelectorAll("#appSidebar .sidebar-link").forEach((link) => {
    link.addEventListener("click", () => {
        const sidebar = document.getElementById("appSidebar");
        if (!sidebar || typeof bootstrap === "undefined") {
            return;
        }

        const offcanvas = bootstrap.Offcanvas.getInstance(sidebar);
        if (offcanvas) {
            offcanvas.hide();
        }
    });
});

const onlyDigits = (value) => value.replace(/\D/g, "");

const formatPhone = (value) => {
    const digits = onlyDigits(value).slice(0, 11);

    if (digits.length <= 2) {
        return digits;
    }

    if (digits.length <= 7) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
    }

    if (digits.length <= 10) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
    }

    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
};

const formatCpf = (value) => {
    const digits = onlyDigits(value).slice(0, 11);

    if (digits.length <= 3) {
        return digits;
    }

    if (digits.length <= 6) {
        return `${digits.slice(0, 3)}.${digits.slice(3)}`;
    }

    if (digits.length <= 9) {
        return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
    }

    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
};

const formatCnpj = (value) => {
    const digits = onlyDigits(value).slice(0, 14);

    if (digits.length <= 2) {
        return digits;
    }

    if (digits.length <= 5) {
        return `${digits.slice(0, 2)}.${digits.slice(2)}`;
    }

    if (digits.length <= 8) {
        return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5)}`;
    }

    if (digits.length <= 12) {
        return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8)}`;
    }

    return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
};

const applyMask = (input) => {
    const mask = input.dataset.mask;
    const value = input.value || "";

    if (mask === "phone") {
        input.value = formatPhone(value);
        return;
    }

    if (mask === "cpf") {
        input.value = formatCpf(value);
        return;
    }

    if (mask === "cnpj") {
        input.value = formatCnpj(value);
    }
};

document.querySelectorAll("input[data-mask]").forEach((input) => {
    applyMask(input);
    input.addEventListener("input", () => applyMask(input));
});

document.querySelectorAll("[data-password-toggle-button]").forEach((button) => {
    const targetId = button.dataset.target;
    const target = document.getElementById(targetId);
    const label = button.querySelector("[data-password-toggle-label]");

    if (!target) {
        return;
    }

    button.addEventListener("click", () => {
        const isPassword = target.type === "password";
        target.type = isPassword ? "text" : "password";
        button.setAttribute("aria-pressed", String(isPassword));
        button.setAttribute("aria-label", isPassword ? "Ocultar senha" : "Mostrar senha");

        if (label) {
            label.textContent = isPassword ? "Ocultar" : "Mostrar";
        }
    });
});
