// Nav solid on scroll
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  if (window.scrollY > 50) {
    nav.style.background = 'rgba(12, 10, 9, 0.95)';
    nav.style.backdropFilter = 'blur(12px)';
    nav.style.borderBottom = '1px solid #292524';
  } else {
    nav.style.background = 'transparent';
    nav.style.backdropFilter = 'none';
    nav.style.borderBottom = 'none';
  }
});

// Mobile menu toggle
document.getElementById('menuToggle').addEventListener('click', () => {
  document.getElementById('mobileMenu').classList.toggle('hidden');
});
// Close mobile menu on link click
document.querySelectorAll('#mobileMenu a').forEach(a => {
  a.addEventListener('click', () => {
    document.getElementById('mobileMenu').classList.add('hidden');
  });
});

// Waitlist form handler
async function submitWaitlist(email, msgEl) {
  msgEl.classList.remove('hidden');
  msgEl.textContent = 'Inscription en cours...';

  try {
    const resp = await fetch('https://api.climbetter.com/api/v1/waitlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await resp.json();

    if (resp.ok) {
      msgEl.textContent = 'Bienvenue ! Tu seras parmi les premiers.';
      msgEl.style.color = '#22c55e';
    } else {
      msgEl.textContent = data.detail || 'Erreur, reessaie.';
      msgEl.style.color = '#ef4444';
    }
  } catch (e) {
    msgEl.textContent = 'Erreur reseau. Verifie ta connexion.';
    msgEl.style.color = '#ef4444';
  }
}

document.getElementById('heroForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const email = document.getElementById('heroEmail').value;
  submitWaitlist(email, document.getElementById('heroMsg'));
  document.getElementById('heroEmail').value = '';
});

document.getElementById('ctaForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const email = document.getElementById('ctaEmail').value;
  submitWaitlist(email, document.getElementById('ctaMsg'));
  document.getElementById('ctaEmail').value = '';
});

// Fade-in on scroll (IntersectionObserver)
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
