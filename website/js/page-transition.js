document.addEventListener("DOMContentLoaded", () => {
  const links = document.querySelectorAll("a[href]");

  links.forEach((link) => {
    const href = link.getAttribute("href");

    if (
      href &&
      !href.startsWith("#") &&
      !href.startsWith("http") &&
      !link.hasAttribute("target")
    ) {
      link.addEventListener("click", (e) => {
        e.preventDefault();

        document.body.classList.add("fade-out");

        setTimeout(() => {
          window.location.href = href;
        }, 180);
      });
    }
  });
});