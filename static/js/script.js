// Email Automation JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Password toggle visibility
    const passwordFields = document.querySelectorAll('input[type="password"]');
    passwordFields.forEach(function(field) {
        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'btn btn-outline-secondary btn-sm ms-2';
        toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
        toggleButton.addEventListener('click', function() {
            if (field.type === 'password') {
                field.type = 'text';
                toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else {
                field.type = 'password';
                toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });
        
        const parent = field.parentElement;
        if (parent.classList.contains('input-group')) {
            parent.appendChild(toggleButton);
        }
    });
    
    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('a[href*="delete_client"]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this client? This action cannot be undone.')) {
                event.preventDefault();
            }
        });
    });
}); 