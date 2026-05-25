/* ============================================================
   Arnio Main — Navigation, Mobile Menu, Scroll Behavior
   ============================================================ */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {

    // ── Sticky nav shadow on scroll ──────────────────────────
    const nav = document.querySelector('.top-nav');
    if (nav) {
      let ticking = false;
      window.addEventListener('scroll', function () {
        if (!ticking) {
          window.requestAnimationFrame(function () {
            if (window.scrollY > 10) {
              nav.classList.add('scrolled');
            } else {
              nav.classList.remove('scrolled');
            }
            ticking = false;
          });
          ticking = true;
        }
      });
    }

    // ── Mobile hamburger menu ────────────────────────────────
    const hamburger = document.querySelector('.nav-hamburger');
    const mobileMenu = document.querySelector('.mobile-menu');

    if (hamburger && mobileMenu) {
      hamburger.addEventListener('click', function () {
        const isOpen = mobileMenu.classList.contains('open');
        mobileMenu.classList.toggle('open');
        hamburger.setAttribute('aria-expanded', !isOpen);
        hamburger.innerHTML = isOpen ? '☰' : '✕';
        document.body.style.overflow = isOpen ? '' : 'hidden';
      });

      // Close menu when clicking a link
      mobileMenu.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', function () {
          mobileMenu.classList.remove('open');
          hamburger.setAttribute('aria-expanded', 'false');
          hamburger.innerHTML = '☰';
          document.body.style.overflow = '';
        });
      });
    }

    // ── Active nav link highlighting ─────────────────────────
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a, .mobile-menu a').forEach(function (link) {
      const href = link.getAttribute('href');
      if (href === currentPage || (currentPage === '' && href === 'index.html')) {
        link.classList.add('active');
      }
    });

    // ── Smooth scroll for anchor links ───────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
      anchor.addEventListener('click', function (e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth' });
          // Update URL without triggering scroll
          history.pushState(null, '', this.getAttribute('href'));
        }
      });
    });

    // ── Sidebar active section tracking (docs pages) ─────────
    const sidebarLinks = document.querySelectorAll('.sidebar-nav-link');
    if (sidebarLinks.length > 0) {
      const sections = [];
      sidebarLinks.forEach(function (link) {
        const id = link.getAttribute('href');
        if (id && id.startsWith('#')) {
          const section = document.querySelector(id);
          if (section) sections.push({ el: section, link: link });
        }
      });

      if (sections.length > 0) {
        let rafPending = false;
        window.addEventListener('scroll', function () {
          if (!rafPending) {
            window.requestAnimationFrame(function () {
              const scrollPos = window.scrollY + 120;
              let activeSection = sections[0];

              for (let i = 0; i < sections.length; i++) {
                if (sections[i].el.offsetTop <= scrollPos) {
                  activeSection = sections[i];
                }
              }

              sidebarLinks.forEach(function (l) { l.classList.remove('active'); });
              if (activeSection) activeSection.link.classList.add('active');

              rafPending = false;
            });
            rafPending = true;
          }
        });
      }
    }
  });
})();
