(async function() {
  const state = initPage();

  // Parse URL
  const params = new URLSearchParams(location.search);
  const mode = params.get('mode') || 'full';
  const topicFilter = (params.get('t') || '').split(',').filter(Boolean);

  // Load data
  let allQuestions, explanations, topicsMeta;
  try {
    const [qq, ex, tt] = await Promise.all([
      fetchData('../data/questions.json'),
      fetchData('../data/explanations.json'),
      fetchData('../data/topics.json'),
    ]);
    allQuestions = qq.data;
    explanations = ex.data;
    topicsMeta = tt.data;
  } catch (e) {
    document.querySelector('.container').innerHTML = '<div class="card"><h2>数据加载失败</h2><p>请刷新页面重试。</p></div>';
    console.error(e);
    return;
  }

  // 过滤掉重复题：is_duplicate_of 指向另一条题的，不重复显示
  // mistakes docx 是 complete 的子集，is_common_mistake 已同步到对应 complete 题
  const uniqueQuestions = allQuestions.filter(q => !q.is_duplicate_of);

  // Build question pool by mode
  let pool, modeTitle, isMock = false, isBrowse = false;
  switch (mode) {
    case 'easy':
      // 优先取 complete 那条（避免 mistakes 子集重复）
      pool = uniqueQuestions.filter(q => q.is_common_mistake);
      modeTitle = '易错题';
      break;
    case 'topic':
      pool = uniqueQuestions.filter(q => q.topics.some(t => topicFilter.includes(t)));
      modeTitle = '分类：' + topicFilter.map(t => (topicsMeta[t]?.zh || t)).join('、');
      break;
    case 'mock':
      pool = shuffle(uniqueQuestions).slice(0, 50);
      modeTitle = '模拟考试 (50)';
      isMock = true;
      break;
    case 'wrong':
      pool = uniqueQuestions.filter(q => state.wrongAnswers.includes(q.id));
      modeTitle = '我的错题本';
      break;
    case 'images':
      pool = uniqueQuestions.filter(q => q.stem_img);
      modeTitle = '带图题审核';
      break;
    case 'browse':
      pool = uniqueQuestions;
      modeTitle = '快速浏览';
      isBrowse = true;
      // 浏览模式答案已预填，自动跳不适用
      document.getElementById('auto-switch')?.classList.add('hidden');
      break;
    default:
      // 完整练习 = complete docx 全部 + mistakes 独有的几条（不在 complete 里）
      pool = uniqueQuestions;
      modeTitle = '完整练习';
  }
  if (pool.length === 0) {
    if (mode === 'wrong') {
      // 保留 header，让空态卡片落在做题卡片本来的位置
      document.getElementById('mode-title').textContent = modeTitle;
      document.title = `${modeTitle}　新泽西驾照笔试`;
      // 隐藏 header 里和答题相关的控件
      document.getElementById('lang-toggle')?.classList.add('hidden');
      document.getElementById('auto-switch')?.classList.add('hidden');
      document.querySelector('.stats')?.classList.add('hidden');

      const hasHistory = (state.totalAttempts || 0) > 0;
      const title = hasHistory ? '错题已清零' : '错题本是空的';
      const desc = hasHistory
        ? `已累计练习 ${state.totalAttempts} 次，目前没有未掌握的题。`
        : '在练习中答错的题会自动收藏到这里，方便定向复习。';

      const qv = document.getElementById('quiz-view');
      qv.innerHTML = `
        <div class="card empty-state">
          <div class="empty-mark" aria-hidden="true">
            <svg viewBox="0 0 48 48" width="36" height="36">
              <circle cx="24" cy="24" r="22" fill="none" stroke="currentColor" stroke-width="1.2"/>
              <path d="M16 24l6 6 12-14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="empty-kicker">错题本</div>
          <h2 class="empty-title">${title}</h2>
          <p class="empty-desc">${desc}</p>
          <div class="empty-actions">
            <a class="btn primary" href="quiz.html?mode=full">开始完整练习</a>
            <a class="btn" href="quiz.html?mode=mock">模拟考试</a>
          </div>
          <a class="empty-back" href="index.html">← 回首页</a>
        </div>
      `;
      qv.classList.remove('hidden');
      // 空态下后续 IIFE 提前 return，需要单独绑 header 返回按钮
      document.getElementById('back-btn').addEventListener('click', () => {
        location.href = 'index.html';
      });
    } else {
      document.querySelector('.container').innerHTML = `<div class="card"><h2>${modeTitle}</h2><p>暂无可用题目。回到 <a href="index.html">首页</a>。</p></div>`;
    }
    return;
  }
  document.getElementById('mode-title').textContent = modeTitle;
  document.title = `${modeTitle}　新泽西驾照笔试`;

  // 顺序切换控件只在 mode='full' 显示
  const orderToggle = document.getElementById('order-toggle');
  const supportsOrderToggle = (mode === 'full' || !mode);
  if (supportsOrderToggle) orderToggle.classList.remove('hidden');

  function applyOrder(p) {
    if (isMock) return p;
    if (isBrowse) return sequentialOrder(p);  // 浏览模式默认按手册顺序
    if (supportsOrderToggle && state.orderMode === 'sequential') {
      return sequentialOrder(p);
    }
    return weightedShuffle(p, state);
  }

  // Apply ordering
  let order = applyOrder(pool);

  // Per-session state
  const session = {
    questions: order,
    current: 0,
    answers: {},  // qid -> 'A'|'B'|...
  };

  // 浏览模式：每道题预填正确答案，渲染时自动出绿色 + 解析
  if (isBrowse) {
    for (const q of order) {
      if (q.answer) session.answers[q.id] = q.answer;
    }
  }

  // Render question
  function renderQuestion() {
    const q = session.questions[session.current];
    const total = session.questions.length;
    const answered = Object.keys(session.answers).length;
    const correct = Object.entries(session.answers).filter(([qid, a]) => {
      const qq = session.questions.find(qx => qx.id == qid);
      return qq && qq.answer === a;
    }).length;
    const wrong = answered - correct;

    document.getElementById('prog-cur').textContent = session.current + 1;
    document.getElementById('prog-tot').textContent = total;
    // 浏览模式：进度按"翻到第几题"算（answered 在初始化时已全部预填 = 100%，无意义）
    const progressPct = isBrowse
      ? ((session.current + 1) / total) * 100
      : (answered / total) * 100;
    document.getElementById('progress-fill').style.width = `${progressPct}%`;
    if (isBrowse) {
      document.getElementById('correct-count').textContent = '—';
      document.getElementById('wrong-count').textContent = '—';
    } else if (!isMock) {
      document.getElementById('correct-count').textContent = correct;
      document.getElementById('wrong-count').textContent = wrong;
    }
    document.getElementById('qnum').textContent = `第 ${session.current + 1} 题${q.type === 'tf' ? '　判断题' : ''}`;
    const imgBadge = document.getElementById('img-badge');
    imgBadge.classList.toggle('hidden', !q.stem_img);

    // Stem image (image left / text right; mobile: stack)
    const stemRow = document.getElementById('stem-row');
    const stemImg = document.getElementById('stem-img');
    if (q.stem_img) {
      stemImg.src = `../data/images/${q.stem_img}`;
      stemImg.alt = `Question image: ${q.stem_img}`;
      stemRow.classList.remove('no-img');
    } else {
      stemRow.classList.add('no-img');
    }

    // Stem text (split bilingual; if only one language present, render as primary text)
    const stemEl = document.getElementById('stem');
    const parts = splitBilingual(q.stem);
    stemEl.innerHTML = '';
    stemEl.classList.toggle('bilingual', !!(parts.en && parts.zh));
    if (parts.en) {
      const enEl = document.createElement('span');
      enEl.className = 'en';
      enEl.textContent = parts.en;
      stemEl.appendChild(enEl);
    }
    if (parts.zh) {
      const zhEl = document.createElement('span');
      zhEl.className = 'zh';
      zhEl.textContent = parts.zh;
      stemEl.appendChild(zhEl);
    }
    if (!parts.en && !parts.zh) {
      stemEl.textContent = q.stem;
    }

    // Options
    const optsEl = document.getElementById('options');
    optsEl.innerHTML = '';
    const userAns = session.answers[q.id];
    const letters = q.type === 'tf' ? ['T', 'F'] : ['A', 'B', 'C', 'D'];
    const visible = q.type === 'tf' ? q.options.slice(0, 2) : q.options;

    visible.forEach((text, i) => {
      if (q.type !== 'tf' && !text) return;
      const letter = letters[i];
      const btn = document.createElement('button');
      btn.className = 'option';
      btn.disabled = !!userAns && !isMock;
      if (userAns) {
        if (isMock) {
          // In mock mode, just highlight selected — no correctness
          if (letter === userAns) btn.classList.add('selected');
        } else {
          if (letter === q.answer) btn.classList.add('correct');
          else if (letter === userAns) btn.classList.add('wrong');
        }
      }
      const letterEl = document.createElement('span');
      letterEl.className = 'option-letter';
      letterEl.textContent = letter;
      const textEl = document.createElement('span');
      textEl.className = 'option-text';
      // SR-only state label so screen readers get feedback (sighted users see color + glyph).
      if (userAns && !isMock) {
        const srState = document.createElement('span');
        srState.className = 'sr-only';
        srState.textContent = letter === q.answer ? ' 正确答案' : (letter === userAns ? ' 你的错误答案' : '');
        if (srState.textContent) btn.appendChild(srState);
      }
      const oparts = splitBilingual(text);
      if (oparts.en && oparts.zh) textEl.classList.add('bilingual');
      if (oparts.en) {
        const e = document.createElement('span');
        e.className = 'opt-en';
        e.textContent = oparts.en;
        textEl.appendChild(e);
      }
      if (oparts.zh) {
        const z = document.createElement('span');
        z.className = 'opt-zh';
        z.textContent = oparts.zh;
        textEl.appendChild(z);
      }
      if (!oparts.en && !oparts.zh) textEl.textContent = text;
      btn.appendChild(letterEl);
      btn.appendChild(textEl);
      btn.addEventListener('click', () => onAnswer(letter));
      optsEl.appendChild(btn);
    });

    // Explanation + knowledge card (only outside mock mode; feedback is via color highlight)
    const ex = document.getElementById('explanation');
    const kn = document.getElementById('knowledge');
    if (userAns && !isMock) {
      renderExplanation(q, ex);
      renderKnowledge(q, kn);
    } else {
      ex.classList.add('hidden');
      kn.classList.add('hidden');
    }

    // Buttons
    document.getElementById('prev-btn').disabled = session.current === 0;
    const nextBtn = document.getElementById('next-btn');
    let nextLabel;
    if (session.current === total - 1) {
      nextLabel = answered === total ? '查看结果' : '下一题';
    } else {
      nextLabel = '下一题';
    }
    nextBtn.innerHTML = `<span>${nextLabel}</span><svg class="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18l6-6-6-6"/></svg>`;
    document.getElementById('jump-input').max = total;
    document.getElementById('jump-input').value = session.current + 1;
    document.getElementById('jumper-total').textContent = `/ ${total}`;

    // Mock submit bar
    if (isMock) {
      let submitBar = document.getElementById('mock-submit-bar');
      if (!submitBar) {
        submitBar = document.createElement('div');
        submitBar.id = 'mock-submit-bar';
        submitBar.className = 'mock-submit-bar';
        submitBar.innerHTML = `
          <span class="ms-status">已答 <strong id="ms-answered">0</strong> / <strong id="ms-total">0</strong></span>
          <button class="btn primary" id="ms-submit-btn">提交考试</button>
        `;
        document.querySelector('.below-card').prepend(submitBar);
        document.getElementById('ms-submit-btn').addEventListener('click', submitMock);
      }
      document.getElementById('ms-answered').textContent = Object.keys(session.answers).length;
      document.getElementById('ms-total').textContent = total;
    }

  }

  function renderExplanation(q, el) {
    if (!q.explanation_key || !explanations[q.explanation_key]) {
      el.classList.add('hidden');
      return;
    }
    const ex = explanations[q.explanation_key];
    el.classList.remove('hidden');
    el.innerHTML = `
      <div class="label">解析</div>
      <div class="body">
        <span class="zh">${ex.zh}</span>
        <span class="en">${ex.en}</span>
      </div>
      <div class="source"><span>${ex.source_label}</span>${ex.source_url ? `<a href="${ex.source_url}" target="_blank" rel="noopener">查看手册 <svg class="icon icon-sm" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17L17 7"/><path d="M7 7h10v10"/></svg></a>` : ''}</div>
    `;
    // Unit conversion hint if question mentions feet
    if (/\b(\d+)\s*(feet|ft|英尺)\b/i.test(q.stem)) {
      const m = q.stem.match(/\b(\d+)\s*(feet|ft|英尺)\b/i);
      if (m) {
        const ft = parseInt(m[1], 10);
        const m_val = (ft * 0.3048).toFixed(1);
        const hintEl = document.createElement('div');
        hintEl.className = 'hint';
        hintEl.textContent = `${ft} 英尺 ≈ ${m_val} 米`;
        el.appendChild(hintEl);
      }
    }
  }

  function renderKnowledge(q, el) {
    if (!q.explanation_key) return el.classList.add('hidden');
    const ex = explanations[q.explanation_key];
    if (!ex || !ex.card) return el.classList.add('hidden');
    const rows = ex.card.rows.map(r =>
      `<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`
    ).join('');
    el.classList.remove('hidden');
    el.innerHTML = `
      <div class="label">知识点</div>
      <div class="card-title">${ex.card.title}</div>
      <table>${rows}</table>
    `;
  }

  let autoAdvanceTimer = null;
  function onAnswer(letter) {
    const q = session.questions[session.current];
    const isReanswer = !!session.answers[q.id];
    if (isReanswer && !isMock) return;
    session.answers[q.id] = letter;
    state.totalAttempts = (state.totalAttempts || 0) + 1;
    if (!isMock) {
      if (letter !== q.answer) {
        if (!state.wrongAnswers.includes(q.id)) state.wrongAnswers.push(q.id);
      } else {
        state.wrongAnswers = state.wrongAnswers.filter(id => id !== q.id);
      }
      for (const t of q.topics) {
        state.topicProgress[t] = state.topicProgress[t] || { seen: 0, correct: 0 };
        state.topicProgress[t].seen += 1;
        if (letter === q.answer) state.topicProgress[t].correct += 1;
      }
      saveState(state);
    }
    renderQuestion();

    // Auto advance
    if (state.autoAdvance && !isBrowse && session.current < session.questions.length - 1) {
      if (autoAdvanceTimer) clearTimeout(autoAdvanceTimer);
      const delay = isMock ? 500 : 1000;
      autoAdvanceTimer = setTimeout(() => {
        autoAdvanceTimer = null;
        nextQ();
      }, delay);
    }
  }

  function nextQ() {
    const total = session.questions.length;
    if (session.current < total - 1) {
      session.current++;
      renderQuestion();
    } else if (Object.keys(session.answers).length === total) {
      if (isMock) stopMockTimer();
      showSummary();
    }
  }

  function submitMock() {
    const total = session.questions.length;
    const answered = Object.keys(session.answers).length;
    if (answered < total) {
      if (!confirm(`还有 ${total - answered} 题未答，确认提交？`)) return;
    }
    stopMockTimer();
    showSummary();
  }
  function prevQ() {
    if (session.current > 0) { session.current--; renderQuestion(); }
  }
  function jumpQ(n) {
    const total = session.questions.length;
    const idx = Math.max(0, Math.min(total - 1, n - 1));
    session.current = idx;
    renderQuestion();
  }

  let mockReviewFilter = 'all';

  const RESULT_CHECK_SVG = `<svg viewBox="0 0 48 48" width="36" height="36"><circle cx="24" cy="24" r="22" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M16 24l6 6 12-14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  function showSummary() {
    const swap = () => {
      _populateSummary();
      document.getElementById('quiz-view').classList.add('hidden');
      document.getElementById('summary-view').classList.remove('hidden');
    };
    if (document.startViewTransition) {
      document.startViewTransition(swap);
    } else {
      swap();
    }
  }

  function _populateSummary() {
    const total = session.questions.length;
    let correct = 0;
    for (const q of session.questions) {
      if (session.answers[q.id] === q.answer) correct++;
    }
    const pct = total ? Math.round((correct / total) * 100) : 0;
    const wrong = total - correct;

    const markEl = document.getElementById('result-mark');
    const kickerEl = document.getElementById('result-kicker');
    const scoreEl = document.getElementById('result-score');
    const titleEl = document.getElementById('result-title');
    const badgeEl = document.getElementById('result-badge');
    const descEl = document.getElementById('result-desc');
    const reviewBtn = document.getElementById('review-btn');
    const mockReviewCard = document.getElementById('mock-review-card');

    // Reset shared state
    scoreEl.classList.add('hidden');
    titleEl.classList.add('hidden');
    badgeEl.classList.add('hidden');
    reviewBtn.classList.add('hidden');
    mockReviewCard.classList.add('hidden');
    markEl.innerHTML = RESULT_CHECK_SVG;

    if (isBrowse) {
      // Browse complete — no score, just acknowledgement
      markEl.className = 'result-mark';
      kickerEl.textContent = '快速浏览';
      titleEl.classList.remove('hidden');
      titleEl.textContent = '已浏览完所有题';
      descEl.textContent = `共 ${total} 题，已全部看过。`;
    } else if (isMock) {
      const passed = pct >= 80;
      markEl.className = 'result-mark ' + (passed ? 'pass' : 'fail');
      kickerEl.textContent = '模拟考试';
      scoreEl.classList.remove('hidden');
      scoreEl.innerHTML = `${correct}<span class="result-score-total"> / ${total}</span>`;
      badgeEl.classList.remove('hidden');
      badgeEl.className = 'result-badge ' + (passed ? 'pass' : 'fail');
      badgeEl.textContent = passed ? '达到 NJ 通过线 (≥ 80%)' : '未达 NJ 通过线 (80%)';

      let durSec = null;
      let durTxt = '';
      if (timerStart) {
        durSec = Math.floor(((timerEnd || Date.now()) - timerStart) / 1000);
        durTxt = ` · 用时 ${formatDuration(durSec)}`;
      }
      descEl.textContent = `${pct}% 正确${durTxt}`;

      state.mockExamHistory.push({
        date: new Date().toISOString().slice(0, 10),
        score: correct, total, durationSec: durSec,
      });
      saveState(state);

      mockReviewFilter = 'all';
      document.querySelectorAll('#review-filter button').forEach(b => {
        b.classList.toggle('active', b.dataset.f === 'all');
      });
      renderMockReview();
      mockReviewCard.classList.remove('hidden');
    } else {
      // full / easy / topic / wrong
      markEl.className = 'result-mark';
      kickerEl.textContent = modeTitle;
      scoreEl.classList.remove('hidden');
      scoreEl.innerHTML = `${correct}<span class="result-score-total"> / ${total}</span>`;
      descEl.textContent = wrong > 0
        ? `正确率 ${pct}% · ${wrong} 道错题已记录`
        : `正确率 ${pct}% · 全部答对`;
      if (wrong > 0) reviewBtn.classList.remove('hidden');
    }

    document.getElementById('review-list').classList.add('hidden');
    document.getElementById('review-list').innerHTML = '';
  }

  function renderMockReview() {
    const list = document.getElementById('mock-review-list');
    list.innerHTML = '';

    let cAll = 0, cWrong = 0, cCorrect = 0, cSkipped = 0;
    for (const q of session.questions) {
      cAll++;
      const a = session.answers[q.id];
      if (!a) cSkipped++;
      else if (a === q.answer) cCorrect++;
      else cWrong++;
    }
    document.getElementById('rf-all').textContent = cAll;
    document.getElementById('rf-wrong').textContent = cWrong;
    document.getElementById('rf-correct').textContent = cCorrect;
    document.getElementById('rf-skipped').textContent = cSkipped;

    const filtered = session.questions.filter(q => {
      const a = session.answers[q.id];
      if (mockReviewFilter === 'all') return true;
      if (mockReviewFilter === 'wrong') return a && a !== q.answer;
      if (mockReviewFilter === 'correct') return a === q.answer;
      if (mockReviewFilter === 'skipped') return !a;
      return true;
    });

    if (filtered.length === 0) {
      list.innerHTML = '<div class="mr-empty">无相应题目</div>';
      return;
    }

    filtered.forEach(q => {
      const origIdx = session.questions.indexOf(q) + 1;
      const a = session.answers[q.id];
      const status = !a ? 'skipped' : (a === q.answer ? 'correct' : 'wrong');
      const statusLabel = !a ? '·' : (a === q.answer ? '✓' : '✗');
      const stemParts = splitBilingual(q.stem);
      const stemTxt = (stemParts.zh || stemParts.en || q.stem).replace(/</g, '&lt;');

      const item = document.createElement('div');
      item.className = 'mr-item';
      item.innerHTML = `
        <div class="mr-row" data-toggle>
          <span class="mr-status ${status}">${statusLabel}</span>
          <span class="mr-num">#${origIdx}</span>
          <span class="mr-stem">${stemTxt}</span>
          <svg class="mr-toggle" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
        </div>
      `;

      const detail = document.createElement('div');
      detail.className = 'mr-detail hidden';
      const letters = q.type === 'tf' ? ['T', 'F'] : ['A', 'B', 'C', 'D'];
      const yourTxt = a ? (q.options[letters.indexOf(a)] || '') : '';
      const correctTxt = q.options[letters.indexOf(q.answer)] || '';
      let html = '';
      if (a) {
        const yp = splitBilingual(yourTxt);
        html += `<div class="mr-d-row"><span class="mr-d-tag ${a === q.answer ? 'correct' : 'your'}">你答 ${a}</span><span class="mr-d-text">${(yp.zh || yp.en || yourTxt).replace(/</g, '&lt;')}</span></div>`;
      } else {
        html += `<div class="mr-d-row"><span class="mr-d-tag skipped">未答</span><span class="mr-d-text">—</span></div>`;
      }
      if (!a || a !== q.answer) {
        const cp = splitBilingual(correctTxt);
        html += `<div class="mr-d-row"><span class="mr-d-tag correct">正确 ${q.answer}</span><span class="mr-d-text">${(cp.zh || cp.en || correctTxt).replace(/</g, '&lt;')}</span></div>`;
      }
      if (q.explanation_key && explanations[q.explanation_key]) {
        const ex = explanations[q.explanation_key];
        html += `<div class="mr-d-explanation">${ex.zh}</div>`;
      }
      detail.innerHTML = html;
      item.appendChild(detail);

      item.querySelector('[data-toggle]').addEventListener('click', () => {
        const open = !detail.classList.contains('hidden');
        detail.classList.toggle('hidden', open);
        item.classList.toggle('open', !open);
      });

      list.appendChild(item);
    });
  }

  // Mock review filter
  document.querySelectorAll('#review-filter button').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.f === mockReviewFilter) return;
      mockReviewFilter = btn.dataset.f;
      document.querySelectorAll('#review-filter button').forEach(b => {
        b.classList.toggle('active', b === btn);
      });
      renderMockReview();
    });
  });

  function showReview() {
    const list = document.getElementById('review-list');
    list.classList.remove('hidden');
    list.innerHTML = '';
    const wrongs = [];
    for (const q of session.questions) {
      const a = session.answers[q.id];
      if (a && a !== q.answer) wrongs.push({ q, your: a });
    }
    if (wrongs.length === 0) {
      list.innerHTML = '<div class="review-item">全部答对，完美！</div>';
      return;
    }
    for (const { q, your } of wrongs) {
      const letters = q.type === 'tf' ? ['T', 'F'] : ['A', 'B', 'C', 'D'];
      const yourText = q.options[letters.indexOf(your)] || '';
      const correctText = q.options[letters.indexOf(q.answer)] || '';
      const div = document.createElement('div');
      div.className = 'review-item';
      const safeStem = q.stem.replace(/</g, '&lt;');
      const safeYour = yourText.replace(/</g, '&lt;');
      const safeCorrect = correctText.replace(/</g, '&lt;');
      div.innerHTML = `
        <div class="review-q">
          ${q.stem_img ? `<img src="../data/images/${q.stem_img}" alt="">` : ''}
          ${safeStem}
        </div>
        <div class="review-ans"><span class="tag your">${your}</span><span>${safeYour}</span></div>
        <div class="review-ans"><span class="tag correct">${q.answer}</span><span>${safeCorrect}</span></div>
      `;
      list.appendChild(div);
    }
  }

  function restart() {
    const swap = () => {
      session.current = 0;
      session.answers = {};
      document.getElementById('summary-view').classList.add('hidden');
      document.getElementById('mock-review-card')?.classList.add('hidden');
      document.getElementById('pass-msg')?.classList.add('hidden');
      if (mode === 'mock') {
        order = shuffle(uniqueQuestions).slice(0, 50);
        session.questions = order;
        timerStart = null;
        timerEnd = null;
        const timerEl = document.getElementById('mock-timer');
        timerEl.textContent = '00:00';
        timerEl.classList.remove('hidden');
        timerEl.classList.add('idle');
        document.getElementById('quiz-view').classList.add('hidden');
        document.getElementById('mock-intro-view').classList.remove('hidden');
        renderMockIntro();
      } else {
        order = applyOrder(pool);
        session.questions = order;
        document.getElementById('quiz-view').classList.remove('hidden');
        renderQuestion();
      }
    };
    if (document.startViewTransition) document.startViewTransition(swap);
    else swap();
  }

  // === Events ===
  document.getElementById('back-btn').addEventListener('click', () => {
    if (Object.keys(session.answers).length > 0 && !confirm('返回首页？当前进度将丢失。')) return;
    location.href = 'index.html';
  });
  document.getElementById('prev-btn').addEventListener('click', prevQ);
  document.getElementById('next-btn').addEventListener('click', nextQ);

  // === Swipe-to-navigate：纯手势检测，无视觉拖拽，瞬切 ===
  (() => {
    const card = document.querySelector('#quiz-view .card');
    if (!card) return;
    const THRESH = 50;
    const ANGLE_DEG = 30;

    let sx = 0, sy = 0;
    let armed = false;

    card.addEventListener('touchstart', (e) => {
      if (e.touches.length !== 1) return;
      sx = e.touches[0].clientX;
      sy = e.touches[0].clientY;
      armed = true;
    }, { passive: true });

    card.addEventListener('touchend', (e) => {
      if (!armed) return;
      armed = false;
      const t = e.changedTouches[0];
      const dx = t.clientX - sx;
      const dy = t.clientY - sy;
      if (Math.abs(dx) < THRESH) return;
      const angle = Math.atan2(Math.abs(dy), Math.abs(dx)) * 180 / Math.PI;
      if (angle >= ANGLE_DEG) return;

      const total = session.questions.length;
      const atFirst = session.current === 0;
      const allAnswered = Object.keys(session.answers).length === total;
      const atLast = session.current === total - 1 && !allAnswered;

      if (dx < 0 && !atLast) nextQ();
      else if (dx > 0 && !atFirst) prevQ();
    }, { passive: true });

    card.addEventListener('touchcancel', () => { armed = false; }, { passive: true });
  })();

  document.getElementById('jump-input').addEventListener('change', (e) => {
    jumpQ(parseInt(e.target.value, 10));
  });
  document.getElementById('redo-btn').addEventListener('click', restart);
  document.getElementById('review-btn').addEventListener('click', showReview);
  document.getElementById('home-btn').addEventListener('click', () => {
    location.href = 'index.html';
  });

  // Auto-advance toggle
  const autoCb = document.getElementById('auto-cb');
  autoCb.checked = !!state.autoAdvance;
  autoCb.addEventListener('change', () => {
    state.autoAdvance = autoCb.checked;
    saveState(state);
    if (!autoCb.checked && autoAdvanceTimer) {
      clearTimeout(autoAdvanceTimer);
      autoAdvanceTimer = null;
    }
  });

  // Language toggle
  document.querySelectorAll('#lang-toggle button').forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      state.languageDisplay = lang;
      applyLanguage(lang);
      saveState(state);
      updateLangButtons();
    });
  });
  function updateLangButtons() {
    document.querySelectorAll('#lang-toggle button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lang === state.languageDisplay);
    });
  }
  updateLangButtons();

  // Order toggle (only visible in full mode)
  function updateOrderButtons() {
    document.querySelectorAll('#order-toggle button').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.order === state.orderMode);
    });
  }
  if (supportsOrderToggle) {
    document.querySelectorAll('#order-toggle button').forEach(btn => {
      btn.addEventListener('click', () => {
        if (btn.dataset.order === state.orderMode) return;
        state.orderMode = btn.dataset.order;
        saveState(state);
        updateOrderButtons();
        // Re-apply ordering and stay on first unanswered question
        const currentQid = session.questions[session.current]?.id;
        session.questions = applyOrder(pool);
        const newIdx = session.questions.findIndex(q => q.id === currentQid);
        session.current = newIdx >= 0 ? newIdx : 0;
        renderQuestion();
      });
    });
    updateOrderButtons();
  }

  // Report error
  document.getElementById('report-btn').addEventListener('click', () => {
    const q = session.questions[session.current];
    openErrorReport(q.id);
  });

  // TTS
  document.getElementById('tts-btn').addEventListener('click', () => {
    const q = session.questions[session.current];
    const parts = splitBilingual(q.stem);
    const lang = state.languageDisplay === 'zh' ? 'zh' : 'en';
    const text = (lang === 'zh' ? parts.zh : parts.en) || q.stem;
    speakText(text, lang);
  });

  // Keyboard — ASDF mapping for left-hand selection, 1234 also works
  const ASDF_MAP = { A: 'A', S: 'B', D: 'C', F: 'D' };
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (document.getElementById('quiz-view').classList.contains('hidden')) return;
    const q = session.questions[session.current];
    const k = e.key.toUpperCase();
    if (q.type === 'tf') {
      if (k === 'A' || e.key === '1') { onAnswer('T'); e.preventDefault(); return; }
      if (k === 'S' || e.key === '2') { onAnswer('F'); e.preventDefault(); return; }
    } else {
      if (k in ASDF_MAP) { onAnswer(ASDF_MAP[k]); e.preventDefault(); return; }
      if (['1','2','3','4'].includes(e.key)) { onAnswer('ABCD'[parseInt(e.key)-1]); e.preventDefault(); return; }
    }
    if (e.key === 'ArrowRight' || e.key === 'Enter') { nextQ(); e.preventDefault(); }
    else if (e.key === 'ArrowLeft') { prevQ(); e.preventDefault(); }
  });

  // Mock exam timer — starts only after 开始考试 click, not on page entry
  let timerStart = null;
  let timerEnd = null;
  let timerInterval = null;

  function startMockTimer() {
    timerStart = Date.now();
    timerEnd = null;
    const timerEl = document.getElementById('mock-timer');
    timerEl.classList.remove('idle', 'hidden');
    timerEl.textContent = '00:00';
    timerInterval = setInterval(() => {
      const sec = Math.floor((Date.now() - timerStart) / 1000);
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      timerEl.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }, 1000);
  }

  function stopMockTimer() {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    if (timerStart && !timerEnd) timerEnd = Date.now();
  }

  function formatDuration(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    if (m === 0) return `${s} 秒`;
    return `${m} 分 ${String(s).padStart(2,'0')} 秒`;
  }

  // Mock intro: show before exam begins. Timer placeholder visible in idle state.
  if (isMock) {
    document.getElementById('quiz-view').classList.add('hidden');
    document.getElementById('mock-intro-view').classList.remove('hidden');
    const timerEl = document.getElementById('mock-timer');
    timerEl.textContent = '00:00';
    timerEl.classList.remove('hidden');
    timerEl.classList.add('idle');
    // mock 模式下对错实时统计无意义，整段隐藏
    document.getElementById('correct-count').classList.add('hidden');
    document.getElementById('wrong-count').classList.add('hidden');
    renderMockIntro();
  }

  function renderMockIntro() {
    const histEl = document.getElementById('mock-intro-history');
    const hist = state.mockExamHistory || [];
    if (hist.length > 0) {
      const recent = hist.slice(-3).reverse();
      histEl.classList.remove('hidden');
      histEl.innerHTML = '<div class="hist-title">最近记录</div>' + recent.map(h => {
        const pct = Math.round((h.score / h.total) * 100);
        const passed = pct >= 80;
        const dur = h.durationSec ? ' · ' + formatDuration(h.durationSec) : '';
        return `<div class="hist-row"><span>${h.date}</span><span class="${passed ? 'pass' : 'fail'}">${h.score}/${h.total} · ${pct}%${dur}</span></div>`;
      }).join('');
    } else {
      histEl.classList.add('hidden');
    }
  }

  document.getElementById('mock-start-btn')?.addEventListener('click', () => {
    document.getElementById('mock-intro-view').classList.add('hidden');
    document.getElementById('quiz-view').classList.remove('hidden');
    startMockTimer();
    renderQuestion();
  });

  // Handle hash navigation (#qid=N) — jump to question with that id
  if (location.hash.startsWith('#qid=')) {
    const targetId = parseInt(location.hash.slice(5), 10);
    const idx = session.questions.findIndex(q => q.id === targetId);
    if (idx >= 0) session.current = idx;
  }

  renderQuestion();
  // 数据已就绪，render 完成才显露 quiz-view（避免加载时空白卡片闪烁）
  if (!isMock) {
    document.getElementById('quiz-view').classList.remove('hidden');
  }
})();
