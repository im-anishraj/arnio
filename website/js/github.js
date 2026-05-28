/* ============================================================
   Arnio GitHub Integration — Real-time Stats & Contributors
   ============================================================ */

(function () {
  'use strict';

  const REPO = 'im-anishraj/arnio';
  const CACHE_KEY_STATS = 'arnio_github_stats';
  const CACHE_KEY_CONTRIBUTORS = 'arnio_github_contributors_v2';
  const CACHE_DURATION = 1000 * 60 * 60; // 1 hour
  const CONTRIBUTORS_PAGE_SIZE = 100;

  /**
   * Fetch data from GitHub API with basic caching
   */
  async function fetchGitHubData(endpoint, cacheKey) {
    let cachedData = null;
    let cachedTimestamp = 0;

    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const parsed = JSON.parse(cached);
        cachedData = parsed.data;
        cachedTimestamp = parsed.timestamp;

        if (Date.now() - cachedTimestamp < CACHE_DURATION) {
          return cachedData;
        }
      }
    } catch (error) {
      try {
        localStorage.removeItem(cacheKey);
      } catch (storageError) {
        // Ignore storage failures; the network request below can still recover.
      }
    }

    try {
      const response = await fetch(`https://api.github.com/repos/${REPO}${endpoint}`);
      if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);
      const data = await response.json();

      try {
        localStorage.setItem(cacheKey, JSON.stringify({
          data,
          timestamp: Date.now()
        }));
      } catch (storageError) {
        // Fresh API data is still usable even if browser storage is unavailable.
      }

      return data;
    } catch (error) {
      return cachedData;
    }
  }

  /**
   * Fetch all pages from a paginated GitHub API endpoint with basic caching.
   */
  async function fetchGitHubPages(endpoint, cacheKey, perPage = CONTRIBUTORS_PAGE_SIZE) {
    let cachedData = null;
    let cachedTimestamp = 0;

    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const parsed = JSON.parse(cached);
        cachedData = parsed.data;
        cachedTimestamp = parsed.timestamp;

        if (Date.now() - cachedTimestamp < CACHE_DURATION) {
          return cachedData;
        }
      }
    } catch (error) {
      try {
        localStorage.removeItem(cacheKey);
      } catch (storageError) {
        // Ignore storage failures; the network request below can still recover.
      }
    }

    try {
      const results = [];
      let nextUrl = `https://api.github.com/repos/${REPO}${endpoint}?per_page=${perPage}`;

      while (nextUrl) {
        const response = await fetch(nextUrl);
        if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);

        const data = await response.json();
        results.push(...data);

        const linkHeader = response.headers.get('Link');
        const nextMatch = linkHeader && linkHeader.match(/<([^>]+)>;\s*rel="next"/);
        nextUrl = nextMatch ? nextMatch[1] : null;
      }

      try {
        localStorage.setItem(cacheKey, JSON.stringify({
          data: results,
          timestamp: Date.now()
        }));
      } catch (storageError) {
        // Fresh API data is still usable even if browser storage is unavailable.
      }

      return results;
    } catch (error) {
      return cachedData;
    }
  }

  /**
   * Update repository stats (stars, forks)
   */
  async function updateRepoStats() {
    const stats = await fetchGitHubData('', CACHE_KEY_STATS);
    if (!stats) return;

    const starElements = document.querySelectorAll('.gh-stars-count');
    const forkElements = document.querySelectorAll('.gh-forks-count');

    starElements.forEach(el => {
      el.textContent = stats.stargazers_count.toLocaleString();
      el.classList.add('loaded');
    });

    forkElements.forEach(el => {
      el.textContent = stats.forks_count.toLocaleString();
      el.classList.add('loaded');
    });
  }

  /**
   * Update contributors grid
   */
  async function updateContributors() {
    const contributors = await fetchGitHubPages('/contributors', CACHE_KEY_CONTRIBUTORS);
    const container = document.getElementById('contributors-container');

    if (!container) return;

    if (!contributors) {
      container.innerHTML = '';

      const fallback = document.createElement('p');
      fallback.className = 'contributors-loading';
      fallback.append('Contributor data is temporarily unavailable. View contributors on ');

      const link = document.createElement('a');
      link.href = `https://github.com/${REPO}/graphs/contributors`;
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = 'GitHub';

      fallback.appendChild(link);
      fallback.append('.');
      container.appendChild(fallback);
      return;
    }

    // Clear loading state if any
    container.innerHTML = '';

    const grid = document.createElement('div');
    grid.className = 'contributors-dynamic-grid';

    contributors.forEach(user => {
      const link = document.createElement('a');
      link.href = user.html_url;
      link.target = '_blank';
      link.rel = 'noopener';
      link.className = 'contributor-item';
      link.title = `${user.login} (${user.contributions} contributions)`;

      const img = document.createElement('img');
      img.src = user.avatar_url;
      img.alt = user.login;
      img.loading = 'lazy';
      img.className = 'contributor-avatar';

      link.appendChild(img);
      grid.appendChild(link);
    });

    container.appendChild(grid);
  }

  // Initialize
  document.addEventListener('DOMContentLoaded', () => {
    updateRepoStats();
    updateContributors();
  });

})();
