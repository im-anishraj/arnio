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

      function closeMobileMenu() {
        mobileMenu.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
        hamburger.setAttribute('aria-label', 'Open menu');
        hamburger.innerHTML = '☰';
        document.body.style.overflow = '';
      }

      hamburger.addEventListener('click', function () {
        const isOpen = mobileMenu.classList.contains('open');
        if (isOpen) {
          closeMobileMenu();
        } else {
          mobileMenu.classList.add('open');
          hamburger.setAttribute('aria-expanded', 'true');
          hamburger.setAttribute('aria-label', 'Close menu');
          hamburger.innerHTML = '✕';
          document.body.style.overflow = 'hidden';
        }
      });

      // Close menu when clicking a link
      mobileMenu.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', function () {
          closeMobileMenu();
        });
      });

      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && mobileMenu.classList.contains('open')) {
          closeMobileMenu();
          hamburger.focus();
        }
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

          const prefersReducedMotion =
            window.matchMedia('(prefers-reduced-motion: reduce)').matches;

          target.scrollIntoView({
            behavior: prefersReducedMotion ? 'auto' : 'smooth'
          });

          history.pushState(null, '', this.getAttribute('href'));
        }
      });
    });
    // ── Scroll-to-top button ───────────────────────────────────
  const scrollTopBtn = document.createElement('button');

  scrollTopBtn.className = 'scroll-top-btn';
  scrollTopBtn.type = 'button';
  scrollTopBtn.setAttribute('aria-label', 'Scroll to top');

  scrollTopBtn.innerHTML = '↑';

  document.body.appendChild(scrollTopBtn);

  const threshold = 300;
  let scrollBtnTicking = false;

  function updateScrollTopButton() {
    if (window.scrollY > threshold) {
      scrollTopBtn.classList.add('visible');
    } else {
      scrollTopBtn.classList.remove('visible');
    }
  }
  
  window.addEventListener('scroll', function () {
    if (!scrollBtnTicking) {
      window.requestAnimationFrame(function () {
        updateScrollTopButton();
        scrollBtnTicking = false;
      });

      scrollBtnTicking = true;
    }
  });

  scrollTopBtn.addEventListener('click', function () {
    const prefersReducedMotion =
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    window.scrollTo({
      top: 0,
      behavior: prefersReducedMotion ? 'auto' : 'smooth'
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

          if (section) {
            sections.push({
              el: section,
              link: link
            });
          }
        }
      });

      if (sections.length > 0) {
        let rafPending = false;

        function setActiveLink(activeLink) {
          sidebarLinks.forEach(function (link) {
            link.classList.remove('active');
          });

          if (activeLink) {
            activeLink.classList.add('active');
          }
        }

        function updateActiveSection() {
          const isAtBottom =
            window.innerHeight + window.scrollY >=
            document.documentElement.scrollHeight - 4;

          let activeSection = sections[0];

          if (isAtBottom) {
            activeSection = sections[sections.length - 1];
          } else {
            const scrollPos =
              window.scrollY + window.innerHeight * 0.35;

            for (let i = 0; i < sections.length; i++) {
              if (sections[i].el.offsetTop <= scrollPos) {
                activeSection = sections[i];
              } else {
                break;
              }
            }
          }

          setActiveLink(activeSection.link);
        }

        window.addEventListener('scroll', function () {
          if (!rafPending) {
            window.requestAnimationFrame(function () {
              updateActiveSection();
              rafPending = false;
            });

            rafPending = true;
          }
        });

        window.addEventListener('hashchange', updateActiveSection);

        sidebarLinks.forEach(function (link) {
          link.addEventListener('click', function () {
            setActiveLink(link);
          });
        });

        updateActiveSection();
      }
    }
  });
})();
