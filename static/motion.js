(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealSelector = [
    '.hero-copy', '.search-panel', '.section-heading', '.city-context',
    '.quick-searches', '.status-line', '.destination-card', '.empty-state',
    '.page-intro', '.trip-summary', '.trip-card', '.attribution'
  ].join(',');

  if (!reducedMotion && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    }, { threshold: 0.12, rootMargin: '0px 0px -32px 0px' });

    const watch = root => {
      if (!root) return;
      const nodes = root.matches?.(revealSelector) ? [root] : [];
      nodes.push(...root.querySelectorAll(revealSelector));
      nodes.forEach((node, index) => {
        if (node.classList.contains('scroll-reveal')) return;
        node.classList.add('scroll-reveal');
        if (node.matches('.destination-card, .trip-card')) {
          const siblingIndex = [...node.parentElement.children].indexOf(node);
          node.style.setProperty('--reveal-delay', `${Math.min(siblingIndex * 65, 390)}ms`);
        } else {
          node.style.setProperty('--reveal-delay', `${Math.min(index * 45, 180)}ms`);
        }
        observer.observe(node);
      });
    };

    watch(document);
    const grids = [document.querySelector('#destination-grid'), document.querySelector('#trip-grid')].filter(Boolean);
    const mutations = new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) watch(node);
    })));
    grids.forEach(grid => mutations.observe(grid, { childList: true, subtree: true }));
  }

  if (reducedMotion || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

  for (const grid of [document.querySelector('#destination-grid'), document.querySelector('#trip-grid')].filter(Boolean)) {
    let activeCard = null;
    grid.addEventListener('pointermove', event => {
      if (event.pointerType !== 'mouse') return;
      const card = event.target.closest('.destination-card, .trip-card');
      if (activeCard && activeCard !== card) reset(activeCard);
      activeCard = card;
      if (!card) return;
      const rect = card.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      card.style.setProperty('--tilt-x', `${(-y * 5).toFixed(2)}deg`);
      card.style.setProperty('--tilt-y', `${(x * 6).toFixed(2)}deg`);
    });
    grid.addEventListener('pointerleave', () => {
      if (activeCard) reset(activeCard);
      activeCard = null;
    });
  }

  function reset(card) {
    card.style.removeProperty('--tilt-x');
    card.style.removeProperty('--tilt-y');
  }
})();
