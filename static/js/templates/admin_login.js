// static/js/templates/admin_login.js

document.addEventListener('DOMContentLoaded', function() {
    // Password visibility toggle functionality
    const passwordInput = document.getElementById("passwordInput");
    const togglePassword = document.getElementById("togglePassword");
    const eyeIcon = document.getElementById("eyeIcon");
    
    if (togglePassword) {
        togglePassword.addEventListener("click", function() {
            // Toggle password visibility
            if (passwordInput.type === "password") {
                passwordInput.type = "text";
                eyeIcon.innerHTML = `
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                `;
            } else {
                passwordInput.type = "password";
                eyeIcon.innerHTML = `
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                `;
            }
        });
    }

    // Add animation for login button
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.addEventListener("mouseover", function() {
            this.classList.add("shadow-xl");
            this.classList.add("scale-105");
            this.classList.remove("shadow-lg");
        });

        submitButton.addEventListener("mouseout", function() {
            this.classList.remove("shadow-xl");
            this.classList.remove("scale-105");
            this.classList.add("shadow-lg");
        });
    }

    // Form validation
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const password = passwordInput.value.trim();
            if (!password) {
                e.preventDefault();
                
                // Shake animation for empty password
                passwordInput.classList.add('border-red-500');
                passwordInput.classList.add('animate-shake');
                
                setTimeout(() => {
                    passwordInput.classList.remove('animate-shake');
                }, 500);
            }
        });
        
        // Remove error styling on input
        passwordInput.addEventListener('input', function() {
            this.classList.remove('border-red-500');
        });
    }
});