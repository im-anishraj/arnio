document.addEventListener("DOMContentLoaded", () => {
  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  // Entry animation
  if (!prefersReducedMotion) {
    document.body.classList.add("page-enter");
  }

  const links = document.querySelectorAll("a[href]");

  links.forEach((link) => {
    link.addEventListener("click", (event) => {
      const href = link.getAttribute("href");

      // Ignore invalid links
      if (!href || href.startsWith("#")) {
        return;
      }

      // Skip non-page-navigation links
      if (
        href.startsWith("mailto:") ||
        href.startsWith("tel:") ||
        href.startsWith("javascript:") ||
        link.hasAttribute("download")
      ) {
        return;
      }

      // Skip external links
      try {
        const url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) {
          return;
        }
      } catch (e) {
        return;
      }

      // Preserve new-tab / modifier behavior
      if (
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey ||
        event.button !== 0 ||
        link.target === "_blank"
      ) {
        return;
      }

      // Skip transition for reduced motion
      if (prefersReducedMotion) {
        return;
      }

      event.preventDefault();

      document.body.classList.add("page-exit");

      setTimeout(() => {
        window.location.href = href;
      }, 180);
    });
  });
});
