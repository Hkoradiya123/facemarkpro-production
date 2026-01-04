// Highlight active link manually if not using server-side logic
document.querySelectorAll('.menu-item').forEach(link => {
  if (link.href === window.location.href) {
    link.classList.add('active');
  }
});

// Dark/Light Theme Toggle (if not already implemented)
function toggleDarkMode() {
  document.body.classList.toggle('dark');
  localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
}

window.addEventListener('DOMContentLoaded', () => {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    document.body.classList.add('dark');
    document.getElementById('themeToggleCheckbox').checked = true;
  }
});
