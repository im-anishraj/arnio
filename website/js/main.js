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

    // Scroll reveal for landing page feature cards
    const featureList = document.querySelector('[data-scroll-reveal]');
    const prefersReducedMotion =
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (featureList) {
      const featureCards = featureList.querySelectorAll('.card');

      featureCards.forEach(function (card, index) {
        card.style.setProperty('--feature-card-index', index);
      });

      if ('IntersectionObserver' in window && !prefersReducedMotion) {
        featureList.classList.add('is-reveal-ready');
        let visibleCards = 0;

        const featureObserver = new IntersectionObserver(function (entries, observer) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add('is-visible');
              observer.unobserve(entry.target);
              visibleCards += 1;

              if (visibleCards === featureCards.length) {
                window.setTimeout(function () {
                  featureList.classList.remove('is-reveal-ready');
                }, 900);
              }
            }
          });
        }, {
          rootMargin: '0px 0px -12% 0px',
          threshold: 0.18
        });

        featureCards.forEach(function (card) {
          featureObserver.observe(card);
        });
      } else {
        featureCards.forEach(function (card) {
          card.classList.add('is-visible');
        });
      }
    }

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
