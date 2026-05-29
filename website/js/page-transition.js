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