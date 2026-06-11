const searchInput = document.getElementById("docs-search");
const resultsBox = document.getElementById("search-results");

if (searchInput && resultsBox) {
  searchInput.setAttribute("aria-controls", "search-results");
  searchInput.setAttribute("aria-expanded", "false");
  searchInput.setAttribute("aria-autocomplete", "list");
  resultsBox.setAttribute("role", "listbox");
  resultsBox.id = "search-results";

  const searchIndex = [
    { title: "Installation", page: "docs.html#install" },
    { title: "Quickstart", page: "docs.html#quickstart" },
    { title: "CSV Reading", page: "docs.html#csv" },
    { title: "Chunked CSV", page: "docs.html#chunked" },
    { title: "JSONL and Parquet", page: "docs.html#jsonl-parquet" },
    { title: "ArFrame", page: "docs.html#frames" },
    { title: "Cleaning", page: "docs.html#cleaning" },
    { title: "Quality Reports", page: "docs.html#quality" },
    { title: "Schema Validation", page: "docs.html#schema" },
    { title: "Integrations", page: "docs.html#integrations" },

    { title: "read_csv", page: "api.html#io" },
    { title: "read_csv_chunked", page: "api.html#io" },
    { title: "scan_csv", page: "api.html#io" },
    { title: "ArFrame API", page: "api.html#frame" },
    { title: "Conversion", page: "api.html#conversion" },
    { title: "Pipeline", page: "api.html#pipeline" },
    { title: "auto_clean", page: "api.html#quality" },
    { title: "profile", page: "api.html#quality" },
    { title: "DateTime", page: "api.html#schema" },
    { title: "Email", page: "api.html#schema" },
    { title: "Exceptions", page: "api.html#exceptions" },
  ];

  let selectedIndex = -1;

  function render(items) {
    resultsBox.innerHTML = "";

    if (!items.length) {
      resultsBox.classList.remove("show");
      searchInput.setAttribute("aria-expanded", "false");
      return;
    }

    items.forEach((item) => {
      const link = document.createElement("a");
      link.className = "search-result";
      link.href = item.page;
      link.textContent = item.title;
      link.setAttribute("role", "option");
      link.setAttribute("aria-selected", "false");

      resultsBox.appendChild(link);
    });

    resultsBox.classList.add("show");
    searchInput.setAttribute("aria-expanded", "true");
  }

  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();

    if (!q) {
      resultsBox.classList.remove("show");
      searchInput.setAttribute("aria-expanded", "false");
      return;
    }

    const matches = searchIndex.filter((item) =>
      item.title.toLowerCase().includes(q),
    );

    selectedIndex = -1;
    render(matches);
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      searchInput.focus();
    }

    if (
      document.activeElement !== searchInput &&
      !resultsBox.contains(document.activeElement)
    ) {
      return;
    }

    const results = [...document.querySelectorAll(".search-result")];

    if (!results.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = (selectedIndex + 1) % results.length;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = (selectedIndex - 1 + results.length) % results.length;
    }

    results.forEach((r) => {
      r.classList.remove("active");
      r.setAttribute("aria-selected", "false");
    });

    if (selectedIndex >= 0) {
      results[selectedIndex].classList.add("active");
      results[selectedIndex].focus();
      results[selectedIndex].setAttribute("aria-selected", "true");
    }

    if (e.key === "Enter" && selectedIndex >= 0) {
      window.location.href = results[selectedIndex].getAttribute("href");
    }

    if (e.key === "Escape") {
      selectedIndex = -1;
      results.forEach((r) => {
        r.classList.remove("active");
        r.setAttribute("aria-selected", "false");
      });
      resultsBox.classList.remove("show");
      searchInput.setAttribute("aria-expanded", "false");
      searchInput.focus();
    }
  });
}
