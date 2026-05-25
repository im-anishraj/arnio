/* ============================================================
   Arnio GitHub Integration — Real-time Stats & Contributors
   ============================================================ */

(function () {
  'use strict';

  const REPO = 'im-anishraj/arnio';
  const CACHE_KEY_STATS = 'arnio_github_stats';
  const CACHE_KEY_CONTRIBUTORS = 'arnio_github_contributors';
  const CACHE_DURATION = 1000 * 60 * 60; // 1 hour

  /**
   * Fetch data from GitHub API with basic caching
   */
  async function fetchGitHubData(endpoint, cacheKey) {
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      const { data, timestamp } = JSON.parse(cached);
      if (Date.now() - timestamp < CACHE_DURATION) {
        return data;
      }
    }

    try {
      const response = await fetch(`https://api.github.com/repos/${REPO}${endpoint}`);
      if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);
      const data = await response.json();

      localStorage.setItem(cacheKey, JSON.stringify({
        data,
        timestamp: Date.now()
      }));

      return data;
    } catch (error) {
      console.error(`Failed to fetch from GitHub (${endpoint}):`, error);
      return cached ? JSON.parse(cached).data : null;
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
    const contributors = await fetchGitHubData('/contributors?per_page=100', CACHE_KEY_CONTRIBUTORS);
    const container = document.getElementById('contributors-container');

    if (!container || !contributors) return;

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
