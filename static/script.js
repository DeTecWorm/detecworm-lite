// --- Lógica del Tema Claro / Oscuro ---
function toggleTheme() {
    const html = document.documentElement;
    const icon = document.getElementById('themeIcon');
    const text = document.getElementById('themeText');
    const textMobile = document.getElementById('themeTextMobile');

    if (html.classList.contains('dark')) {
        html.classList.remove('dark');
        localStorage.setItem('theme', 'light');
        if(icon) icon.className = 'fa-solid fa-sun text-amber-500';
        if(text) text.innerText = 'Claro';
        if(textMobile) textMobile.innerText = 'Claro';
    } else {
        html.classList.add('dark');
        localStorage.setItem('theme', 'dark');
        if(icon) icon.className = 'fa-solid fa-moon text-amber-400';
        if(text) text.innerText = 'Oscuro';
        if(textMobile) textMobile.innerText = 'Oscuro';
    }
}

// Cargar preferencia al inicio
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('theme') === 'light') {
        document.documentElement.classList.remove('dark');
        const icon = document.getElementById('themeIcon');
        const text = document.getElementById('themeText');
        const textMobile = document.getElementById('themeTextMobile');
        
        if(icon) icon.className = 'fa-solid fa-sun text-amber-500';
        if(text) text.innerText = 'Claro';
        if(textMobile) textMobile.innerText = 'Claro';
    }
});

// --- Lógica Menú Hamburguesa y Modales ---
function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    if (menu) menu.classList.toggle('hidden');
}

function openQrModal() {
    const qrModal = document.getElementById('qrModal');
    const mobileMenu = document.getElementById('mobileMenu');
    const errorBox = document.getElementById('nodoError');
    const input = document.getElementById('codigoNodo');

    if (errorBox) errorBox.classList.add('hidden');
    if (input) input.value = '';

    if (qrModal) qrModal.classList.remove('hidden');
    if (mobileMenu) mobileMenu.classList.add('hidden');
}

function closeQrModal() {
    const qrModal = document.getElementById('qrModal');
    if (qrModal) qrModal.classList.add('hidden');
}

// --- Función para Generalizar Términos (Adiós nombres específicos por ahora) ---
function generalizarTexto(texto) {
    if (!texto) return '';
    return texto
        .replace(/cogollero/gi, 'plaga')
        .replace(/maíz/gi, 'cultivo')
        .replace(/maiz/gi, 'cultivo')
        .replace(/sorgo/gi, 'cultivo');
}

// --- Lógica de Manejo de Imagen ---
let selectedFile = null;
let isAnalyzing = false; // Bandera Antispam

function triggerFileInput() {
    document.getElementById('imageInput').click();
}

function previewImage(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.getElementById('preview');
            img.src = e.target.result;
            
            document.getElementById('uploadPrompt').classList.add('hidden');
            document.getElementById('previewContainer').classList.remove('hidden');
            document.getElementById('analyzeBtn').disabled = false;
        }
        reader.readAsDataURL(file);
    }
}

function clearImage(event) {
    event.stopPropagation();
    const fileInput = document.getElementById('imageInput');
    fileInput.value = '';
    selectedFile = null;
    
    document.getElementById('preview').src = '';
    document.getElementById('previewContainer').classList.add('hidden');
    document.getElementById('uploadPrompt').classList.remove('hidden');
    document.getElementById('analyzeBtn').disabled = true;
    
    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.className = "flex-1 flex flex-col justify-center items-center text-center p-4";
    resultsContainer.innerHTML = `
        <div class="w-12 h-12 bg-slate-100 dark:bg-slate-800/40 text-slate-400 dark:text-slate-600 rounded-full flex items-center justify-center mb-3">
            <i class="fa-solid fa-microscope text-xl"></i>
        </div>
        <p class="text-xs text-slate-500 dark:text-slate-400 max-w-xs leading-relaxed">
            Adjunta una imagen del cultivo y presiona <strong class="text-slate-700 dark:text-slate-300">"Analizar cultivo"</strong> para ver el informe detallado y el plan de acción sugerido.
        </p>
    `;
}

// --- Proceso de Análisis e Inyección de Resultados ---
async function analyzeImage() {
    if (!selectedFile || isAnalyzing) return;
    
    isAnalyzing = true;
    const resultsContainer = document.getElementById('resultsContainer');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const icon = document.getElementById('analyzeIcon');
    const text = document.getElementById('analyzeText');

    analyzeBtn.disabled = true;
    if(icon) icon.className = "fa-solid fa-spinner fa-spin";
    if(text) text.innerText = "Analizando...";

    resultsContainer.className = "flex-1 flex flex-col justify-between space-y-4";
    resultsContainer.innerHTML = `
        <div class="my-auto text-center space-y-3 py-8">
            <div class="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p class="text-xs text-emerald-600 dark:text-emerald-400 font-semibold animate-pulse">Analizando tejido foliar e IA DeTecWorm...</p>
        </div>
    `;

    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch('/analizar', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Error en la respuesta del servidor");

        const data = await response.json();

        // Manejo del Escudo Anti-Basura
        if (data.status === 'error' || data.status === 'warning' || data.es_cultivo === false) {
            resultsContainer.innerHTML = `
                <div class="my-auto text-center space-y-3 py-6">
                    <div class="w-12 h-12 bg-rose-100 dark:bg-rose-950/60 text-rose-500 rounded-full flex items-center justify-center mx-auto border border-rose-300 dark:border-rose-800">
                        <i class="fa-solid fa-shield-halved text-xl"></i>
                    </div>
                    <div class="space-y-1">
                        <h3 class="text-sm font-bold text-rose-600 dark:text-rose-400">Imagen No Válida</h3>
                        <p class="text-xs text-slate-600 dark:text-slate-400 max-w-xs mx-auto">
                            ${generalizarTexto(data.mensaje || data.analisis_visual || "No se detectó una hoja válida. Por favor sube una foto clara.")}
                        </p>
                    </div>
                </div>
            `;
            return;
        }

        // Aplicar generalización a los textos devueltos por la IA
        const diagnosticoGen = generalizarTexto(data.diagnostico || "Anomalía detectada en cultivo");
        const analisisGen = generalizarTexto(data.analisis_visual || "Sin detalles adicionales.");
        const recomendacionGen = generalizarTexto(data.recomendacion || "Monitorear la zona afectada.");

        const riesgo = data.nivel_riesgo || (diagnosticoGen.toLowerCase().includes("sano") ? "verde" : "rojo");
        
        let colorTexto, colorBadge, colorBox, badgeSemaforo;

        if (riesgo === 'rojo') {
            colorTexto = "text-rose-600 dark:text-rose-400";
            colorBadge = "text-rose-600 dark:text-rose-400 bg-rose-100 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/20";
            colorBox = "bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800/40";
            badgeSemaforo = '🔴 Riesgo Severo';
        } else if (riesgo === 'amarillo') {
            colorTexto = "text-amber-600 dark:text-amber-400";
            colorBadge = "text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-500/10 border-amber-300 dark:border-amber-500/20";
            colorBox = "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/40";
            badgeSemaforo = '🟡 Riesgo Moderado';
        } else {
            colorTexto = "text-emerald-600 dark:text-emerald-400";
            colorBadge = "text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/20";
            colorBox = "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/40";
            badgeSemaforo = '🟢 Sano / Bajo Riesgo';
        }

        // Renderizar Respuesta Limpia y Generalizada
        resultsContainer.innerHTML = `
            <div class="space-y-3">
                <div class="bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 rounded-xl p-3.5 flex justify-between items-center">
                    <div>
                        <div class="flex items-center gap-2 mb-0.5">
                            <span class="text-[10px] text-slate-500 uppercase font-semibold tracking-wider">Diagnóstico</span>
                            <span class="text-[10px] font-bold ${colorBadge} px-2 py-0.5 rounded-full">${badgeSemaforo}</span>
                        </div>
                        <p class="text-sm font-bold ${colorTexto}">${diagnosticoGen}</p>
                    </div>
                    <div class="text-right">
                        <span class="text-[10px] text-slate-500 block">Certeza</span>
                        <span class="text-xs font-bold border px-2 py-0.5 rounded-md inline-block ${colorBadge}">
                            ${data.confianza}%
                        </span>
                    </div>
                </div>

                <div class="${colorBox} border rounded-xl p-4 space-y-2">
                    <h3 class="text-xs font-bold ${colorTexto} flex items-center gap-1.5">
                        <i class="fa-solid fa-microscope"></i> Análisis Visual Foliar
                    </h3>
                    <p class="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                        ${analisisGen}
                    </p>
                    <p class="text-xs font-semibold ${colorTexto} pt-1">
                        Daño foliar estimado: ${data.porcentaje_dano || 0}%
                    </p>
                </div>

                <div class="bg-slate-50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800/80 rounded-xl p-4 space-y-1.5">
                    <h3 class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                        <i class="fa-solid fa-lightbulb text-amber-500"></i> Recomendaciones de Manejo
                    </h3>
                    <p class="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                        ${recomendacionGen}
                    </p>
                </div>
            </div>
        `;

        // Guardar en la BD con etiquetas genéricas
        try {
            await fetch('/guardar-consulta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    'diagnostico': diagnosticoGen,
                    'confianza': data.confianza,
                    'cultivo': 'Cultivo General',
                    'nivel_riesgo': riesgo
                })
            });
        } catch (err) {
            console.error("No se pudo guardar la consulta en la BD:", err);
        }

    } catch (error) {
        console.error("Error al procesar la imagen:", error);
        resultsContainer.innerHTML = `
            <div class="my-auto text-center space-y-2 py-6">
                <div class="w-10 h-10 bg-rose-100 dark:bg-rose-950/50 text-rose-500 rounded-full flex items-center justify-center mx-auto border border-rose-300 dark:border-rose-800">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                </div>
                <p class="text-xs text-rose-500 font-semibold">Ocurrió un error al analizar la imagen.</p>
                <p class="text-[11px] text-slate-500">Asegúrate de que el servidor FastAPI esté en ejecución.</p>
            </div>
        `;
    } finally {
        isAnalyzing = false;
        analyzeBtn.disabled = false;
        if(icon) icon.className = "fa-solid fa-wand-magic-sparkles";
        if(text) text.innerText = "Analizar cultivo";
    }
}

/* ============================================================
   ACTIVACIÓN DE NODO PRO POR CÓDIGO ÚNICO (carcasa física / QR)
   ------------------------------------------------------------
   100% en el cliente: el estado se guarda en localStorage del
   navegador, así que permanece activo aunque el usuario cierre
   sesión, recargue la página o cierre el navegador.

   IMPORTANTE (seguridad para producción): la lista de códigos
   de abajo es solo una DEMO para desarrollo/pruebas. Cualquier
   persona puede abrir las herramientas de desarrollador y leer
   estos códigos o ejecutar activarPro() manualmente. Para el
   lanzamiento real, la validación debe hacerse contra un
   backend propio (por ejemplo, un endpoint POST /api/validar-nodo
   en app.py que consulte una tabla de códigos emitidos), y esta
   lista debe eliminarse del código del cliente.
   ============================================================ */

// Claves usadas en localStorage (persisten indefinidamente en este navegador)
const PRO_STORAGE_KEY = 'isPro';                 // 'true' | 'false'
const PRO_CODE_STORAGE_KEY = 'nodoActivo';        // ej. "DTW-PRO-0001"

// Lista de ejemplo de códigos válidos de carcasas (demo).
const CODIGOS_PRO_VALIDOS = [
    'DTW-PRO-0001',
    'DTW-PRO-0002',
    'DTW-PRO-0003',
    'DTW-PRO-A1B2',
    'DTW-PRO-DEMO',
];

// Patrón general aceptado en la demo: prefijo DTW-PRO- + 4 o más caracteres alfanuméricos.
// (En producción, quitar esta línea y validar solo contra el backend.)
const PATRON_CODIGO_PRO = /^DTW-PRO-[A-Z0-9]{4,}$/;

function normalizarCodigo(codigo) {
    return (codigo || '').trim().toUpperCase();
}

function esCodigoValido(codigo) {
    const limpio = normalizarCodigo(codigo);
    if (!limpio) return false;
    return CODIGOS_PRO_VALIDOS.includes(limpio) || PATRON_CODIGO_PRO.test(limpio);
}

function esPro() {
    return localStorage.getItem(PRO_STORAGE_KEY) === 'true';
}

function activarPro(codigo) {
    localStorage.setItem(PRO_STORAGE_KEY, 'true');
    localStorage.setItem(PRO_CODE_STORAGE_KEY, codigo);
    aplicarEstadoPro();
}

function desactivarPro() {
    localStorage.removeItem(PRO_STORAGE_KEY);
    localStorage.removeItem(PRO_CODE_STORAGE_KEY);
    aplicarEstadoPro();
}

function validarCodigoNodo(event) {
    event.preventDefault();
    const input = document.getElementById('codigoNodo');
    const errorBox = document.getElementById('nodoError');
    const codigo = normalizarCodigo(input ? input.value : '');

    if (esCodigoValido(codigo)) {
        activarPro(codigo);
        if (errorBox) errorBox.classList.add('hidden');
        closeQrModal();
    } else if (errorBox) {
        errorBox.textContent = 'Código no válido. Verifica el código impreso en la carcasa de tu nodo (formato DTW-PRO-XXXX).';
        errorBox.classList.remove('hidden');
    }
    return false;
}

function simularEscaneoQR() {
    // Demo: simula una lectura exitosa de QR devolviendo un código válido de ejemplo.
    const demo = CODIGOS_PRO_VALIDOS[Math.floor(Math.random() * CODIGOS_PRO_VALIDOS.length)];
    const input = document.getElementById('codigoNodo');
    if (input) input.value = demo;
}

// Aplica visualmente el estado PRO/gratuito en toda la página actual
function aplicarEstadoPro() {
    const activo = esPro();
    const codigoGuardado = localStorage.getItem(PRO_CODE_STORAGE_KEY) || '--';

    // Insignias "PRO" (header, tarjetas de funciones bloqueadas, etc.)
    document.querySelectorAll('.pro-badge, #proBadgeHeader').forEach((el) => {
        el.classList.toggle('hidden', !activo);
    });

    // Paneles bloqueados vs. contenido PRO real (usa data-pro-locked / data-pro-content)
    document.querySelectorAll('[data-pro-locked]').forEach((el) => el.classList.toggle('hidden', activo));
    document.querySelectorAll('[data-pro-content]').forEach((el) => el.classList.toggle('hidden', !activo));

    // Paneles específicos de index.html (predicción avanzada IA + sensores)
    const proLocked = document.getElementById('proLockedPanel');
    const proContent = document.getElementById('proContentPanel');
    if (proLocked) proLocked.classList.toggle('hidden', activo);
    if (proContent) proContent.classList.toggle('hidden', !activo);

    // Texto del botón "Agregar Nodo" -> "Nodo PRO Activo"
    const textoDesktop = document.getElementById('nodoBtnTextDesktop');
    const textoMobile = document.getElementById('nodoBtnTextMobile');
    const textoPerfil = document.getElementById('nodoBtnTextPerfil');
    if (textoDesktop) textoDesktop.textContent = activo ? 'Nodo PRO Activo' : 'Agregar Nodo';
    if (textoMobile) textoMobile.textContent = activo ? 'Nodo PRO Activo' : 'Agregar Nodo (QR)';
    if (textoPerfil) textoPerfil.textContent = activo ? 'Nodo PRO Activo' : 'Activar Nodo';

    // Estado dentro del modal de activación
    const estadoActivo = document.getElementById('nodoEstadoActivo');
    const codigoActualEl = document.getElementById('nodoCodigoActual');
    if (estadoActivo) estadoActivo.classList.toggle('hidden', !activo);
    if (codigoActualEl) codigoActualEl.textContent = codigoGuardado;
}

document.addEventListener('DOMContentLoaded', aplicarEstadoPro);