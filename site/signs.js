(function() {
  initPage();
  document.getElementById('back-btn').addEventListener('click', () => { location.href = 'index.html'; });
  const grid = document.getElementById('signs-grid');
  const pages = [];
  for (let p = 213; p <= 224; p++) pages.push(p);

  pages.forEach((p, idx) => {
    const div = document.createElement('div');
    div.className = 'sign-card';
    div.innerHTML = `
      <img src="../data/images/manual_signs/manual_p${p}.jpg" alt="NJ Driver Manual page ${p}" loading="lazy">
      <div class="pagenum">p${p}</div>
    `;
    div.addEventListener('click', () => openLightbox(idx));
    grid.appendChild(div);
  });

  function openLightbox(startIdx) {
    let idx = startIdx;
    const backdrop = document.createElement('div');
    backdrop.className = 'lightbox-backdrop';
    backdrop.innerHTML = `
      <img class="lightbox-img" alt="">
      <div class="lightbox-controls">
        <button class="nav prev" aria-label="上一张">
          <svg class="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="count"></span>
        <button class="nav next" aria-label="下一张">
          <svg class="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
    `;
    document.body.appendChild(backdrop);

    const img = backdrop.querySelector('.lightbox-img');
    const count = backdrop.querySelector('.count');
    const prevBtn = backdrop.querySelector('.nav.prev');
    const nextBtn = backdrop.querySelector('.nav.next');

    function render() {
      const p = pages[idx];
      img.src = `../data/images/manual_signs/manual_p${p}.jpg`;
      img.alt = `NJ Driver Manual p${p}`;
      count.textContent = `${idx + 1} / ${pages.length}`;
      prevBtn.disabled = idx === 0;
      nextBtn.disabled = idx === pages.length - 1;
    }
    render();

    const close = () => {
      backdrop.classList.add('closing');
      document.removeEventListener('keydown', onKey);
      setTimeout(() => backdrop.remove(), 200);
    };
    const go = (delta) => {
      const ni = idx + delta;
      if (ni >= 0 && ni < pages.length) { idx = ni; render(); }
    };

    // 点任意地方关闭，除了控件区
    backdrop.addEventListener('click', (e) => {
      if (e.target.closest('.lightbox-controls')) return;
      close();
    });
    prevBtn.addEventListener('click', () => go(-1));
    nextBtn.addEventListener('click', () => go(1));

    const onKey = (e) => {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowLeft') go(-1);
      else if (e.key === 'ArrowRight') go(1);
    };
    document.addEventListener('keydown', onKey);

    // Touch swipe
    let touchX = null;
    backdrop.addEventListener('touchstart', (e) => { touchX = e.touches[0].clientX; }, { passive: true });
    backdrop.addEventListener('touchend', (e) => {
      if (touchX === null) return;
      const dx = e.changedTouches[0].clientX - touchX;
      touchX = null;
      if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
    });
  }
})();
