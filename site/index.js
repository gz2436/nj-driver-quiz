(async function() {
  const state = initPage();

  let questions = [];
  let topicsMeta = {};
  try {
    const [qq, tt] = await Promise.all([
      fetchData('../data/questions.json'),
      fetchData('../data/topics.json'),
    ]);
    questions = qq.data;
    topicsMeta = tt.data;
  } catch (e) {
    console.error('Failed to load data:', e);
  }

  const uniqueQuestions = questions.filter(q => !q.is_duplicate_of);
  const topicKeys = Object.keys(topicsMeta).filter(k => k !== 'general');

  document.getElementById('browse-num').textContent = uniqueQuestions.length;
  document.getElementById('easy-num').textContent = uniqueQuestions.filter(q => q.is_common_mistake).length;
  document.getElementById('wrong-num').textContent = state.wrongAnswers.length;
  document.getElementById('topic-num').textContent = topicKeys.length;

  // 始终显示 trace 三段：累计 / 错题 / 上次模考；无数据时用 — 占位
  const lastMock = state.mockExamHistory.length > 0
    ? state.mockExamHistory[state.mockExamHistory.length - 1]
    : null;
  const traceParts = [
    `累计 <strong>${state.totalAttempts || 0}</strong>`,
    `错题 <strong>${state.wrongAnswers.length}</strong>`,
    `上次 <strong>${lastMock ? `${lastMock.score}/${lastMock.total}` : '—/—'}</strong>`,
  ];
  document.getElementById('masthead-trace').innerHTML = traceParts.join(' <span class="trace-dot">·</span> ');

  // Order toggle
  const ctaToggle = document.getElementById('cta-order-toggle');
  function updateOrderButtons() {
    ctaToggle.querySelectorAll('button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.order === state.orderMode);
    });
  }
  updateOrderButtons();
  ctaToggle.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (btn.dataset.order === state.orderMode) return;
      state.orderMode = btn.dataset.order;
      saveState(state);
      updateOrderButtons();
    });
  });

  // Topic modal
  const topicCounts = {};
  for (const q of uniqueQuestions) {
    for (const t of q.topics) topicCounts[t] = (topicCounts[t] || 0) + 1;
  }
  const topicOrder = Object.keys(topicCounts).sort((a, b) => topicCounts[b] - topicCounts[a]);

  document.getElementById('mode-topic-btn').addEventListener('click', (e) => {
    e.preventDefault();
    openTopicModal();
  });

  function openTopicModal() {
    const selected = new Set();
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.innerHTML = `
      <div class="modal modal-topic">
        <div class="modal-topic-head">
          <h2>选择分类</h2>
          <p class="modal-sub">可多选，开始后只练这些主题</p>
        </div>

        <div class="topic-list-head">
          <span class="topic-list-label">分类</span>
          <span class="topic-list-actions">
            <button type="button" class="topic-list-action" id="topic-select-all">全选</button>
            <span class="topic-list-sep" aria-hidden="true">·</span>
            <button type="button" class="topic-list-action" id="topic-select-clear" disabled>清空</button>
            <span class="topic-list-status" id="topic-status">未选</span>
          </span>
        </div>

        <div class="topic-list" id="topic-grid-modal"></div>

        <div class="modal-actions modal-actions-pair">
          <button class="btn" id="topic-cancel">取消</button>
          <button class="btn primary" id="topic-start" disabled>开始练习</button>
        </div>
      </div>
    `;
    document.body.appendChild(backdrop);
    const grid = backdrop.querySelector('#topic-grid-modal');
    const startBtn = backdrop.querySelector('#topic-start');
    const statusEl = backdrop.querySelector('#topic-status');
    const selectAllBtn = backdrop.querySelector('#topic-select-all');
    const clearBtn = backdrop.querySelector('#topic-select-clear');
    const rowMap = new Map();

    function updateStatus() {
      const n = selected.size;
      statusEl.textContent = n === 0 ? '未选' : `已选 ${n} 项`;
      statusEl.classList.toggle('active', n > 0);
      startBtn.disabled = n === 0;
      clearBtn.disabled = n === 0;
      selectAllBtn.disabled = n === topicOrder.length;
      let totalQ = 0;
      for (const t of selected) totalQ += topicCounts[t] || 0;
      startBtn.textContent = n === 0 ? '开始练习' : `开始练习 · ${totalQ} 题`;
    }

    for (const t of topicOrder) {
      const meta = topicsMeta[t] || { zh: t, en: t };
      const row = document.createElement('button');
      row.className = 'topic-row';
      row.type = 'button';
      row.innerHTML = `
        <span class="topic-row-check" aria-hidden="true"></span>
        <span class="topic-row-name">${meta.zh}</span>
        <span class="topic-row-count">${topicCounts[t]}</span>
      `;
      row.addEventListener('click', () => {
        if (selected.has(t)) { selected.delete(t); row.classList.remove('selected'); }
        else { selected.add(t); row.classList.add('selected'); }
        updateStatus();
      });
      grid.appendChild(row);
      rowMap.set(t, row);
    }
    updateStatus();

    selectAllBtn.addEventListener('click', () => {
      for (const t of topicOrder) {
        selected.add(t);
        rowMap.get(t).classList.add('selected');
      }
      updateStatus();
    });
    clearBtn.addEventListener('click', () => {
      selected.clear();
      for (const row of rowMap.values()) row.classList.remove('selected');
      updateStatus();
    });

    const close = () => {
      backdrop.classList.add('closing');
      setTimeout(() => backdrop.remove(), 200);
    };
    backdrop.querySelector('#topic-cancel').addEventListener('click', close);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
    document.addEventListener('keydown', function onEsc(e) {
      if (e.key === 'Escape') { close(); document.removeEventListener('keydown', onEsc); }
    });
    startBtn.addEventListener('click', () => {
      const ts = [...selected].join(',');
      location.href = `quiz.html?mode=topic&t=${encodeURIComponent(ts)}`;
    });
  }

  // Clear data
  document.getElementById('clear-data-btn').addEventListener('click', () => {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.innerHTML = `
      <div class="modal modal-confirm">
        <h2>清除本地数据</h2>
        <p>将清除浏览器中保存的所有数据：错题记录、累计尝试次数、模考历史、语言偏好。此操作不可撤销。</p>
        <p class="confirm-en">Clear all locally-stored data: wrong-answer log, attempts, mock history, language preference. This cannot be undone.</p>
        <div class="modal-actions modal-actions-pair">
          <button class="btn" id="confirm-cancel">取消</button>
          <button class="btn primary danger" id="confirm-clear">确认清除</button>
        </div>
      </div>
    `;
    document.body.appendChild(backdrop);
    function closeWithAnim() {
      backdrop.classList.add('closing');
      setTimeout(() => backdrop.remove(), 200);
    }
    document.getElementById('confirm-cancel').addEventListener('click', closeWithAnim);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeWithAnim(); });
    document.getElementById('confirm-clear').addEventListener('click', () => {
      try { localStorage.removeItem(STORAGE_KEY); } catch(e) {}
      // Keep the backdrop alive (transparent + pointer-events on) until reload
      // so the synthetic click can't leak through to a menu-row underneath.
      backdrop.style.pointerEvents = 'auto';
      backdrop.style.background = 'transparent';
      const isMobile = matchMedia('(max-width: 540px)').matches;

      if (isMobile) {
        // Mobile: static toast, no animation
        backdrop.innerHTML = `<div class="toast"><span class="toast-glyph toast-check" aria-hidden="true"><svg viewBox="0 0 24 24" width="14" height="14"><path d="M5 12l4 4L19 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span class="toast-text">已清除所有数据</span></div>`;
        setTimeout(() => location.reload(), 900);
        return;
      }

      // Desktop: spinner → check animation
      backdrop.innerHTML = `<div class="toast is-animated"><span class="toast-glyph spinner spinner-sm" aria-hidden="true"></span><span class="toast-text">正在清除…</span></div>`;
      const t = backdrop.querySelector('.toast');
      requestAnimationFrame(() => t.classList.add('show'));

      setTimeout(() => {
        const glyph = t.querySelector('.toast-glyph');
        const text = t.querySelector('.toast-text');
        glyph.style.opacity = '0';
        text.style.opacity = '0';
        setTimeout(() => {
          glyph.className = 'toast-glyph toast-check';
          glyph.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M5 12l4 4L19 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
          glyph.style.opacity = '';
          text.textContent = '已清除所有数据';
          text.style.opacity = '';
          t.classList.add('is-done');
        }, 180);
      }, 1200);

      setTimeout(() => {
        t.classList.remove('show');
        setTimeout(() => location.reload(), 280);
      }, 3200);
    });
  });
})();
