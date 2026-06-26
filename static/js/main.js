document.addEventListener('DOMContentLoaded', () => {

    // ── Sidebar toggle ────────────────────────────────────
    const sidebar  = document.getElementById('sidebar');
    const overlay  = document.getElementById('sidebarOverlay');
    const toggler  = document.getElementById('sidebarToggle');

    function openSidebar()  {
        sidebar.classList.add('open');
        overlay.classList.add('visible');
        document.body.style.overflow = 'hidden';
    }
    function closeSidebar() {
        sidebar.classList.remove('open');
        overlay.classList.remove('visible');
        document.body.style.overflow = '';
    }

    if (toggler) {
        toggler.addEventListener('click', () => {
            const isMobile = window.innerWidth <= 768;
            if (isMobile) {
                sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
            } else {
                // Tablet/desktop: alterna sidebar completa vs mini
                document.body.classList.toggle('sidebar-collapsed');
            }
        });
    }
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // Fecha sidebar ao navegar no mobile
    sidebar && sidebar.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768) closeSidebar();
        });
    });

    // ── Marca link ativo (sidebar + barra mobile) ─────────
    const currentPath = window.location.pathname;
    document.querySelectorAll('#sidebar .nav-link, .mobile-nav a').forEach(link => {
        try {
            const lp = new URL(link.href).pathname;
            if (lp !== '/' && currentPath.startsWith(lp)) {
                link.classList.add('active');
            }
        } catch(_) {}
    });

    // ── Auto-dismiss alerts ───────────────────────────────
    document.querySelectorAll('.alert-auto').forEach(el => {
        setTimeout(() => {
            el.style.transition = 'opacity .5s';
            el.style.opacity = 0;
            setTimeout(() => el.remove(), 500);
        }, 3500);
    });

    // ── Inicializa busca de CEP ───────────────────────────
    document.querySelectorAll('[data-cep-input]').forEach(initCepBusca);

    // ── Ajuste ao redimensionar ───────────────────────────
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) closeSidebar();
    });
});

// ─────────────────────────────────────────────────────────
//  Busca de CEP via ViaCEP — reutilizável
//
//  Atributos no campo:
//    data-cep-input                  → ativa a busca automática
//    data-fill-logradouro="#id"      → preenche logradouro
//    data-fill-bairro="#id"          → preenche bairro
//    data-fill-cidade="#id"          → preenche cidade
//    data-fill-uf="#id"              → preenche UF
// ─────────────────────────────────────────────────────────
function initCepBusca(input) {
    const badge = document.createElement('span');
    badge.className = 'cep-status ms-2 small';
    input.parentElement.appendChild(badge);

    input.addEventListener('input', () => {
        const digits = input.value.replace(/\D/g, '');
        // Formata: 00000-000
        input.value = digits.length > 5
            ? digits.slice(0,5) + '-' + digits.slice(5,8)
            : digits;
        if (digits.length === 8) buscarCEP(digits, input, badge);
        else if (digits.length < 8) badge.textContent = '';
    });
}

async function buscarCEP(cep, inputEl, badge) {
    badge.innerHTML = '<span class="text-muted"><span class="spinner-border spinner-border-sm me-1"></span>Buscando…</span>';
    try {
        const res  = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
        const data = await res.json();

        if (data.erro) {
            badge.innerHTML = '<span class="text-danger">❌ CEP não encontrado</span>';
            return;
        }

        const form = inputEl.closest('form');
        const map  = {
            logradouro: data.logradouro,
            bairro:     data.bairro,
            cidade:     data.localidade,
            uf:         data.uf,
        };

        Object.entries(map).forEach(([key, val]) => {
            const sel = inputEl.dataset['fill' + key[0].toUpperCase() + key.slice(1)];
            if (!sel) return;
            const el = (form || document).querySelector(sel);
            if (el && val) {
                el.value = val;
                el.classList.add('cep-preenchido');
                setTimeout(() => el.classList.remove('cep-preenchido'), 1000);
            }
        });

        // Foca no campo número
        const numEl = (form || document).querySelector('[data-cep-numero]');
        if (numEl) setTimeout(() => numEl.focus(), 100);

        badge.innerHTML = `<span class="text-success">✅ ${data.localidade}/${data.uf}</span>`;
    } catch (_) {
        badge.innerHTML = '<span class="text-warning">⚠ Sem conexão com ViaCEP</span>';
    }
}
