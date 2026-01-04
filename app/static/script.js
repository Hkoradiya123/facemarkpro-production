// Theme Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.querySelector('.theme-switch__checkbox');
    const body = document.body;
    const fadeOverlay = document.getElementById('fadeOverlay');
    
    // Load saved theme or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    body.className = savedTheme;
    
    // Set initial toggle state
    if (savedTheme === 'dark') {
        themeToggle.checked = true;
    }
    
    // Theme toggle event listener
    if (themeToggle) {
        themeToggle.addEventListener('change', function() {
            // Add fade overlay during transition
            if (fadeOverlay) {
                fadeOverlay.classList.add('active');
            }
            
            // Change theme immediately to prevent text disappearing
            if (this.checked) {
                body.className = 'dark';
                localStorage.setItem('theme', 'dark');
            } else {
                body.className = 'light';
                localStorage.setItem('theme', 'light');
            }
            
            // Remove fade overlay after a shorter delay
            setTimeout(() => {
                if (fadeOverlay) {
                    fadeOverlay.classList.remove('active');
                }
            }, 150);
        });
    }
});

// Password visibility toggle for faculty
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.querySelector('.eye-icon');
    
    if (passwordInput && eyeIcon) {
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            eyeIcon.textContent = '🙈';
        } else {
            passwordInput.type = 'password';
            eyeIcon.textContent = '👁';
        }
    }
}

// Password visibility toggle for student
function toggleStudentPassword() {
    const passwordInput = document.getElementById('student_password');
    const eyeIcon = document.querySelector('#studentForm .eye-icon');
    
    if (passwordInput && eyeIcon) {
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            eyeIcon.textContent = '🙈';
        } else {
            passwordInput.type = 'password';
            eyeIcon.textContent = '👁';
        }
    }
}

// Remember me functionality for faculty
function storeRememberMe() {
    const rememberMe = document.getElementById('rememberMe');
    const email = document.getElementById('faculty_email');
    
    if (rememberMe && email) {
        if (rememberMe.checked) {
            localStorage.setItem('rememberedEmail', email.value);
        } else {
            localStorage.removeItem('rememberedEmail');
        }
    }
}

// Remember me functionality for student
function storeStudentRememberMe() {
    const rememberMe = document.getElementById('rememberStudent');
    const rollNo = document.getElementById('roll_no');
    
    if (rememberMe && rollNo) {
        if (rememberMe.checked) {
            localStorage.setItem('rememberedRollNo', rollNo.value);
        } else {
            localStorage.removeItem('rememberedRollNo');
        }
    }
}

// Load remembered data
document.addEventListener('DOMContentLoaded', function() {
    // Load remembered faculty email
    const rememberedEmail = localStorage.getItem('rememberedEmail');
    const emailInput = document.getElementById('faculty_email');
    const rememberMe = document.getElementById('rememberMe');
    
    if (rememberedEmail && emailInput) {
        emailInput.value = rememberedEmail;
        if (rememberMe) {
            rememberMe.checked = true;
        }
    }
    
    // Load remembered student roll number
    const rememberedRollNo = localStorage.getItem('rememberedRollNo');
    const rollNoInput = document.getElementById('roll_no');
    const rememberStudent = document.getElementById('rememberStudent');
    
    if (rememberedRollNo && rollNoInput) {
        rollNoInput.value = rememberedRollNo;
        if (rememberStudent) {
            rememberStudent.checked = true;
        }
    }
});

// Mobile responsiveness helpers
function handleMobileLayout() {
    const isMobile = window.innerWidth <= 768;
    const body = document.body;
    
    if (isMobile) {
        body.classList.add('mobile-layout');
    } else {
        body.classList.remove('mobile-layout');
    }
}

// Handle window resize
window.addEventListener('resize', handleMobileLayout);

// Initial mobile layout check
document.addEventListener('DOMContentLoaded', handleMobileLayout);

// Smooth scrolling for mobile
function smoothScrollTo(element) {
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }
}

// Handle form focus on mobile
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[type="text"], input[type="password"]');
    
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            if (window.innerWidth <= 768) {
                setTimeout(() => {
                    smoothScrollTo(this);
                }, 300);
            }
        });
    });
});

// Prevent zoom on input focus (iOS)
document.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[type="text"], input[type="password"]');
    
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            if (window.innerWidth <= 768) {
                const viewport = document.querySelector('meta[name="viewport"]');
                if (viewport) {
                    viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
                }
            }
        });
        
        input.addEventListener('blur', function() {
            if (window.innerWidth <= 768) {
                const viewport = document.querySelector('meta[name="viewport"]');
                if (viewport) {
                    viewport.content = 'width=device-width, initial-scale=1.0';
                }
            }
        });
    });
});

// Enhanced touch interactions for mobile
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('button, input[type="submit"], .role-option');
    
    buttons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.classList.add('touch-active');
        });
        
        button.addEventListener('touchend', function() {
            setTimeout(() => {
                this.classList.remove('touch-active');
            }, 150);
        });
    });
});

// Handle orientation change
window.addEventListener('orientationchange', function() {
    setTimeout(() => {
        handleMobileLayout();
    }, 100);
});

// Keyboard navigation improvements
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.tagName === 'INPUT') {
        const form = e.target.closest('form');
        if (form) {
            const inputs = Array.from(form.querySelectorAll('input[type="text"], input[type="password"]'));
            const currentIndex = inputs.indexOf(e.target);
            
            if (currentIndex < inputs.length - 1) {
                e.preventDefault();
                inputs[currentIndex + 1].focus();
            }
        }
    }
});
