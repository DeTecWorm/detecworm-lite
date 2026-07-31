document.addEventListener('DOMContentLoaded', () => {
    // --- 1. Lógica de Cambio de Tema (Claro / Oscuro) ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const body = document.body;

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        body.classList.remove('dark-mode');
        if (themeIcon) themeIcon.textContent = '🌙';
    } else {
        body.classList.add('dark-mode');
        if (themeIcon) themeIcon.textContent = '☀️';
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            const isDark = body.classList.contains('dark-mode');
            if (themeIcon) themeIcon.textContent = isDark ? '☀️' : '🌙';
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });
    }

    // --- 2. Lógica de Vista Previa y Manejo de Archivo ---
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const fileNameDisplay = document.getElementById('file-name-display');
    const removeImgBtn = document.getElementById('remove-img-btn');
    const resultCard = document.getElementById('result-card');

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    imagePreview.src = event.target.result;
                    fileNameDisplay.textContent = file.name;
                    
                    dropZone.classList.add('hidden');
                    previewContainer.classList.remove('hidden');
                    if (resultCard) resultCard.classList.add('hidden'); // Ocultar resultados previos
                };
                reader.readAsDataURL(file);
            }
        });
    }

    if (removeImgBtn) {
        removeImgBtn.addEventListener('click', () => {
            fileInput.value = '';
            imagePreview.src = '';
            fileNameDisplay.textContent = '';

            previewContainer.classList.add('hidden');
            dropZone.classList.remove('hidden');
            if (resultCard) resultCard.classList.add('hidden');
        });
    }

    // --- 3. Manejo del envío vía AJAX (Fetch) e Inyección de Resultados ---
    const uploadForm = document.getElementById('upload-form');
    const btnSubmit = document.getElementById('btn-submit');

    // Elementos de la tarjeta de resultados
    const resDiagnosis = document.getElementById('res-diagnosis');
    const resConfidence = document.getElementById('res-confidence');
    const resProgressBar = document.getElementById('res-progress-bar');
    const resRecommendation = document.getElementById('res-recommendation');
    const resFilename = document.getElementById('res-filename');

    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(uploadForm);
            
            btnSubmit.disabled = true;
            btnSubmit.textContent = 'Analizando tejido foliar...';

            try {
                const response = await fetch('/predict', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error('Error en el servidor');

                const data = await response.json();

                // Actualizar interfaz con los datos recibidos
                resDiagnosis.textContent = data.diagnosis;
                resConfidence.textContent = `${data.confidence}%`;
                resProgressBar.style.width = `${data.confidence}%`;
                resRecommendation.textContent = data.recommendation;
                resFilename.textContent = data.filename;

                // Mostrar tarjeta de resultados
                resultCard.classList.remove('hidden');
                
                // Hacer scroll suave hacia el resultado
                resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

            } catch (error) {
                console.error(error);
                alert('Hubo un error al procesar la imagen.');
            } finally {
                btnSubmit.disabled = false;
                btnSubmit.textContent = 'Analizar Hoja';
            }
        });
    }
});