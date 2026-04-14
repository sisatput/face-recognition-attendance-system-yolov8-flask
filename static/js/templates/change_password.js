// static/js/templates/change_password.js

document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const currentPasswordInput = document.getElementById("current_password");
    const newPasswordInput = document.getElementById("new_password");
    const confirmPasswordInput = document.getElementById("confirm_password");
    const strengthMeter = document.getElementById("password-strength-meter");
    const strengthText = document.getElementById("password-strength-text");
    const submitButton = document.getElementById("submit-button");
    const passwordMatchStatus = document.getElementById("password-match-status");
    
    // Password validation
    function validatePassword() {
        const password = newPasswordInput.value;
        let strength = 0;
        let feedback = "";

        // Length check
        if (password.length >= 8) {
            strength += 1;
        }

        // Character variety checks
        if (/[A-Z]/.test(password)) strength += 1; // Has uppercase
        if (/[a-z]/.test(password)) strength += 1; // Has lowercase
        if (/[0-9]/.test(password)) strength += 1; // Has number
        if (/[^A-Za-z0-9]/.test(password)) strength += 1; // Has special char

        // Update strength meter
        if (strengthMeter && strengthText) {
            // Reset classes
            strengthMeter.className = "h-2 rounded-full transition-all duration-300";
            
            // Apply appropriate styling based on strength
            if (password.length === 0) {
                strengthMeter.style.width = "0%";
                strengthMeter.classList.add("bg-gray-200");
                feedback = "";
            } else if (strength < 2) {
                strengthMeter.style.width = "25%";
                strengthMeter.classList.add("bg-red-500");
                feedback = "Sangat lemah";
            } else if (strength < 3) {
                strengthMeter.style.width = "50%";
                strengthMeter.classList.add("bg-orange-500");
                feedback = "Lemah";
            } else if (strength < 4) {
                strengthMeter.style.width = "75%";
                strengthMeter.classList.add("bg-yellow-500");
                feedback = "Sedang";
            } else {
                strengthMeter.style.width = "100%";
                strengthMeter.classList.add("bg-green-500");
                feedback = "Kuat";
            }
            
            strengthText.textContent = feedback;
        }
        
        validatePasswordMatch();
        return strength >= 3; // At least medium strength required
    }

    // Password match validation
    function validatePasswordMatch() {
        if (!confirmPasswordInput || !newPasswordInput) return;
        
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (confirmPassword === "") {
            if (passwordMatchStatus) {
                passwordMatchStatus.textContent = "";
                passwordMatchStatus.className = "";
            }
            return false;
        }
        
        const isMatch = newPassword === confirmPassword;
        
        if (passwordMatchStatus) {
            if (isMatch) {
                passwordMatchStatus.textContent = "Password cocok";
                passwordMatchStatus.className = "text-sm text-green-500";
            } else {
                passwordMatchStatus.textContent = "Password tidak cocok";
                passwordMatchStatus.className = "text-sm text-red-500";
            }
        }
        
        // Update submit button state
        if (submitButton) {
            const newPassValid = validatePassword();
            submitButton.disabled = !(isMatch && newPassValid);
            
            if (isMatch && newPassValid) {
                submitButton.classList.remove("opacity-50", "cursor-not-allowed", "bg-gray-400");
                submitButton.classList.add("bg-gradient-to-r", "from-primary-600", "to-primary-700");
            } else {
                submitButton.classList.add("opacity-50", "cursor-not-allowed", "bg-gray-400");
                submitButton.classList.remove("bg-gradient-to-r", "from-primary-600", "to-primary-700");
            }
        }
        
        return isMatch;
    }

    // Attach event listeners for password validation
    if (newPasswordInput) {
        newPasswordInput.addEventListener("input", validatePassword);
    }
    
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener("input", validatePasswordMatch);
    }

    // Show notification function
    function showNotification(message, isSuccess = true) {
        const notification = document.getElementById("notification");
        const notificationText = document.getElementById("notification-text");
        
        if (notification && notificationText) {
            notificationText.textContent = message;
            
            // Set appropriate class based on success/error
            if (isSuccess) {
                notification.classList.remove("bg-red-500");
                notification.classList.add("bg-green-500");
            } else {
                notification.classList.remove("bg-green-500");
                notification.classList.add("bg-red-500");
            }
            
            // Show notification
            notification.classList.remove("hidden");
            
            // Hide after 3 seconds
            setTimeout(() => {
                notification.classList.add("hidden");
            }, 3000);
        }
    }

    // Form submission
    const changePasswordForm = document.getElementById("change-password-form");
    if (changePasswordForm) {
        changePasswordForm.addEventListener("submit", function(e) {
            e.preventDefault();
            
            // Validate form
            if (!currentPasswordInput.value) {
                showNotification("Masukkan password saat ini", false);
                return;
            }
            
            if (!validatePassword()) {
                showNotification("Password baru terlalu lemah", false);
                return;
            }
            
            if (!validatePasswordMatch()) {
                showNotification("Password baru dan konfirmasi tidak cocok", false);
                return;
            }
            
            // Submit form if validation passes
            this.submit();
        });
    }

    // Handle server-side messages
    document.addEventListener("DOMContentLoaded", function() {
        const serverMessage = document.getElementById("server-message");
        if (serverMessage && serverMessage.textContent.trim() !== "") {
            const isSuccess = serverMessage.classList.contains("text-green-500");
            showNotification(serverMessage.textContent, isSuccess);
        }
    });
});