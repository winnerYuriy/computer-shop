document.addEventListener('DOMContentLoaded', function() {
    // Знаходимо поле gallery_images
    const galleryField = document.querySelector('#id_gallery_images');
    
    if (galleryField) {
        // Додаємо підказку
        const helpText = document.createElement('div');
        helpText.style.marginTop = '5px';
        helpText.style.fontSize = '12px';
        helpText.style.color = '#666';
        helpText.innerHTML = `
            <strong>Приклади:</strong><br>
            • Пустий масив: <code>[]</code><br>
            • Одне зображення: <code>["products/photo1.jpg"]</code><br>
            • Декілька: <code>["products/photo1.jpg", "products/photo2.jpg"]</code>
        `;
        galleryField.parentNode.appendChild(helpText);
        
        // Валідація JSON
        galleryField.addEventListener('change', function() {
            try {
                const value = this.value;
                if (value && value.trim()) {
                    JSON.parse(value);
                    this.style.borderColor = '#28a745';
                } else {
                    this.style.borderColor = '#ccc';
                }
            } catch(e) {
                this.style.borderColor = '#dc3545';
                alert('Помилка JSON: ' + e.message);
            }
        });
    }
});