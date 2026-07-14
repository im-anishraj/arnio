const searchInput = document.getElementById("docs-search");
const resultsBox = document.getElementById("search-results");

if (searchInput && resultsBox) {
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
    { title: "Exceptions", page: "api.html#exceptions" }
  ];

  let selectedIndex = -1;

  function closeResults() {
    selectedIndex = -1;
    resultsBox.classList.remove("show");

    resultsBox
      .querySelectorAll(".search-result.active")
      .forEach((result) => {
        result.classList.remove("active");
      });
  }

  function render(items) {
    resultsBox.innerHTML = "";

    if (!items.length) {
      closeResults();
      return;
    }

    items.forEach((item) => {
      const div = document.createElement("div");
      div.className = "search-result";
      div.textContent = item.title;

      div.addEventListener("click", () => {
        closeResults();
        window.location.href = item.page;
      });

      resultsBox.appendChild(div);
    });

    resultsBox.classList.add("show");
  }

  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();

    if (!q) {
      closeResults();
      return;
    }

    const matches = searchIndex.filter((item) =>
      item.title.toLowerCase().includes(q)
    );

    selectedIndex = -1;
    render(matches);
  });

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      searchInput.focus();
    }

    const results = [
      ...resultsBox.querySelectorAll(".search-result")
    ];

    if (!resultsBox.classList.contains("show") || !results.length) {
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = (selectedIndex + 1) % results.length;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex =
        (selectedIndex - 1 + results.length) % results.length;
    }

    results.forEach((result) => {
      result.classList.remove("active");
    });

    if (selectedIndex >= 0) {
      results[selectedIndex].classList.add("active");
    }

    if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault();
      results[selectedIndex].click();
    }

    if (e.key === "Escape") {
      closeResults();
    }
  });
}
