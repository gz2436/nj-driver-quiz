// NJ Driver Quiz — Shared JS utilities

const STORAGE_KEY = 'nj_quiz_v1';

// Fetch a data file, falling back to .sample.json when the main file isn't present.
// A small banner appears when running on samples.
// URL param ?sample=1 forces sample mode regardless of real file availability.
async function fetchData(path) {
  const forceSample = new URLSearchParams(location.search).get('sample') === '1';
  const samplePath = path.replace(/\.json$/, '.sample.json');
  if (forceSample) {
    const r = await fetch(samplePath, { cache: 'no-store' });
    if (r.ok) {
      document.documentElement.dataset.sampleMode = '1';
      return { data: await r.json(), sample: true };
    }
  }
  const r = await fetch(path, { cache: 'no-store' });
  if (r.ok) return { data: await r.json(), sample: false };
  const r2 = await fetch(samplePath, { cache: 'no-store' });
  if (r2.ok) {
    document.documentElement.dataset.sampleMode = '1';
    return { data: await r2.json(), sample: true };
  }
  throw new Error(`Neither ${path} nor ${samplePath} reachable`);
}

// === Inline SVG icons (Lucide style, 1.75 stroke) ===
const ICONS = {
  'arrow-left':   '<path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/>',
  'arrow-right':  '<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>',
  'chevron-left': '<path d="M15 18l-6-6 6-6"/>',
  'chevron-right':'<path d="M9 18l6-6-6-6"/>',
  'bookmark':     '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  'bookmark-filled': '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" fill="currentColor" stroke="none"/>',
  'flag':         '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>',
  'volume':       '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>',
  'check':        '<path d="M20 6L9 17l-5-5"/>',
  'x':            '<path d="M18 6L6 18"/><path d="M6 6l12 12"/>',
  'info':         '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  'search':       '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  'sun':          '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
};

function iconSVG(name, sizeClass = '') {
  const path = ICONS[name];
  if (!path) return '';
  return `<svg class="icon ${sizeClass}" viewBox="0 0 24 24" aria-hidden="true">${path}</svg>`;
}

const DEFAULT_STATE = {
  version: 1,
  disclaimerAccepted: null,
  wrongAnswers: [],          // question IDs
  bookmarks: [],             // question IDs
  topicProgress: {},         // topic → {seen, correct}
  totalAttempts: 0,
  languageDisplay: 'bilingual',  // 'bilingual' | 'zh' | 'en'
  orderMode: 'random',           // 'random' | 'sequential' (完整版可切换)
  autoAdvance: false,            // 答完自动跳下一题
  theme: 'auto',                 // 'auto' | 'light' | 'dark'
  mockExamHistory: [],
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_STATE };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_STATE, ...parsed };
  } catch (e) {
    console.warn('localStorage read failed:', e);
    return { ...DEFAULT_STATE };
  }
}

function saveState(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.warn('localStorage write failed:', e);
  }
}

function applyLanguage(lang) {
  document.body.setAttribute('data-lang', lang);
}

// Split a bilingual string heuristically into English + Chinese parts.
// Examples:
//   "The minimum age: 获取驾照最小年龄为：" → ["The minimum age:", "获取驾照最小年龄为："]
//   "12 ounces of beer 12盎司啤酒" → ["12 ounces of beer", "12盎司啤酒"]
function splitBilingual(text) {
  if (!text) return { en: '', zh: '' };
  const m = text.match(/[一-鿿]/);
  if (!m) return { en: text.trim(), zh: '' };
  const idx = m.index;
  let en = text.slice(0, idx).trim();
  let zh = text.slice(idx).trim();
  // 仅在英文段没有任何字母/数字（纯标点或空白）时才当成中文整段
  if (!/[A-Za-z0-9]/.test(en)) return { en: '', zh: text.trim() };
  // 中式编号修正：把属于中文段开头的字母/数字编号从 EN 段还回 ZH
  // 1. 单字母 + 中文车号量词："A 车" / "B 号"
  const tailLetter = en.match(/\s+([A-Z])$/);
  const headMeasureL = zh.match(/^[车号型类项]/);
  if (tailLetter && headMeasureL) {
    en = en.slice(0, en.length - tailLetter[0].length).trim();
    zh = tailLetter[1] + ' ' + zh;
    return { en, zh };
  }
  // 2. 数字 + 中文量词："6个月" / "25英里" / "10秒" / "1.5倍" / "5-6秒" / "47号公路" / "12盎司"
  const tailNum = en.match(/(?:^|\s)(\d+(?:\.\d+)?(?:\s*[-–~至到]\s*\d+(?:\.\d+)?)?)$/);
  const headMeasureN = zh.match(/^[个月年天秒钟岁分英里周次倍点页米厘里寸尺盎杯瓶罐升度号磅码加块元章条款题公美]/);
  if (tailNum && headMeasureN) {
    en = en.slice(0, tailNum.index).trim();
    zh = tailNum[1] + zh;
  }
  return { en, zh };
}

// Pure random shuffle (Fisher-Yates)
function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Sequential order: complete docx first then mistakes docx, each by source_para_idx
function sequentialOrder(questions) {
  return questions.slice().sort((a, b) => {
    const docA = a.source_doc === 'complete' ? 0 : 1;
    const docB = b.source_doc === 'complete' ? 0 : 1;
    if (docA !== docB) return docA - docB;
    const piA = a.source_para_idx ?? Number.MAX_SAFE_INTEGER;
    const piB = b.source_para_idx ?? Number.MAX_SAFE_INTEGER;
    if (piA !== piB) return piA - piB;
    return (a.id || 0) - (b.id || 0);
  });
}

// Weighted shuffle: questions in state.wrongAnswers appear 2x more often
function weightedShuffle(questions, state) {
  const wrongSet = new Set(state.wrongAnswers);
  const expanded = [];
  for (const q of questions) {
    expanded.push(q);
    if (wrongSet.has(q.id)) expanded.push(q);  // duplicate for higher weight
  }
  const shuffled = shuffle(expanded);
  // Dedup keeping first occurrence
  const seen = new Set();
  const result = [];
  for (const q of shuffled) {
    if (!seen.has(q.id)) {
      seen.add(q.id);
      result.push(q);
    }
  }
  return result;
}

// === Disclaimer modal ===
const DISCLAIMER_HTML = `
<p class="disc-lede zh">本站为社区维护的学习工具，按"现状"提供，与新泽西州 MVC 无任何关联，<br>不构成法律或专业建议。</p>
<p class="disc-lede en">This community study tool is provided "AS IS", is not affiliated with the NJ MVC, and does not constitute legal or professional advice.</p>

<ol class="disc-clauses">
  <li>
    <div class="clause-head">
      <span class="num">1</span>
      <span class="lbl">来源 <em>Source</em></span>
    </div>
    <p class="zh">整理自 <a href="https://www.aiqiang.org/post/nj-driverlicense-written-exam-practice" target="_blank" rel="noopener">aiqiang.org</a>，与 NJ Driver Manual 逐题校验。</p>
    <p class="en">Compiled from aiqiang.org, cross-verified against the NJ Driver Manual.</p>
  </li>
  <li>
    <div class="clause-head">
      <span class="num">2</span>
      <span class="lbl">隐私 <em>Privacy</em></span>
    </div>
    <p class="zh">不上传任何数据，进度仅存于本地浏览器。</p>
    <p class="en">No data uploaded; all progress stays in your browser.</p>
  </li>
  <li>
    <div class="clause-head">
      <span class="num">3</span>
      <span class="lbl">准确性 <em>Accuracy</em></span>
    </div>
    <p class="zh">不保证与实考相同、准确或完整；如有差异以官方手册为准。</p>
    <p class="en">No guarantee of accuracy or that content matches the actual exam.</p>
  </li>
  <li>
    <div class="clause-head">
      <span class="num">4</span>
      <span class="lbl">责任 <em>Liability</em></span>
    </div>
    <p class="zh">使用者自担全部风险。本站及作者不对因使用造成的任何损失承担责任。</p>
    <p class="en">Use at your own risk. Authors are not liable for any damages from use.</p>
  </li>
</ol>

<div class="disc-foot">
  权威参考 <em>Authority</em> &mdash; <a href="https://www.nj.gov/mvc/pdf/license/drivermanual.pdf" target="_blank" rel="noopener">NJ Driver Manual ↗</a>
</div>
`;

function showDisclaimer(state, onAccept) {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.innerHTML = `
    <div class="modal modal-disclaimer">
      <header class="disc-header">
        <h2>免责声明</h2>
        <div class="disc-sub">Disclaimer &mdash; 非官方 Not Official</div>
      </header>
      ${DISCLAIMER_HTML}
      <div class="modal-actions">
        <button class="btn primary disc-agree" id="disclaimer-agree">我同意</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  document.getElementById('disclaimer-agree').addEventListener('click', () => {
    state.disclaimerAccepted = new Date().toISOString().slice(0, 10);
    saveState(state);
    backdrop.remove();
    if (onAccept) onAccept();
  });
}

function ensureDisclaimer(state, onReady) {
  if (state.disclaimerAccepted) {
    if (onReady) onReady();
  } else {
    showDisclaimer(state, onReady);
  }
}

// === TTS ===
function speakText(text, lang) {
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang === 'zh' ? 'zh-CN' : 'en-US';
  u.rate = 0.95;
  speechSynthesis.speak(u);
}

// === Report error (Tally popup) ===
// REPLACE the value below with your Tally form ID (the part after /r/ in the share URL)
// e.g. if the share URL is https://tally.so/r/wXYZ12, then TALLY_FORM_ID = 'wXYZ12'
const TALLY_FORM_ID = 'EkvaeX';

function openErrorReport(questionId) {
  if (TALLY_FORM_ID === 'REPLACE_ME' || !window.Tally) {
    alert(`报错功能尚未配置。题号 #${questionId} 已记录到浏览器控制台。`);
    console.warn('Report:', questionId);
    return;
  }
  const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  window.Tally.openPopup(TALLY_FORM_ID, {
    layout: 'modal',
    width: 500,
    hiddenFields: { qid: String(questionId) },
    overlay: true,
    autoClose: 2000,
    theme: isDark ? 'dark' : 'light',
  });
}

// === Share ===
async function shareSite() {
  const url = location.origin + (location.pathname.replace(/\/[^/]*$/, '/') || '/');
  const title = '新泽西驾照笔试练习';
  const text = '中英对照 NJ 驾照笔试练习，与官方手册交叉校验。';
  if (navigator.share) {
    try {
      await navigator.share({ title, text, url });
      return;
    } catch (e) {
      if (e.name === 'AbortError') return;
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    showToast('链接已复制');
  } catch (e) {
    prompt('复制链接：', url);
  }
}

function showToast(text) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = text;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add('show'), 10);
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 280); }, 1800);
}

// === Footer ===
function getVersionLabel() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}/${m}/${d}`;
}

function renderFooter(state) {
  const existing = document.querySelector('footer.site-footer');
  if (existing) return;
  const footer = document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = `
    <div class="footer-inner">
      <div class="footer-source">
        <span class="footer-label">整理自</span>
        <a href="https://www.aiqiang.org/post/nj-driverlicense-written-exam-practice" target="_blank" rel="noopener">aiqiang.org</a>
        <span class="footer-cross" aria-hidden="true">×</span>
        <a href="https://www.nj.gov/mvc/pdf/license/drivermanual.pdf" target="_blank" rel="noopener">NJ Driver Manual</a>
      </div>
      <nav class="footer-nav">
        <a href="#" id="footer-disclaimer" class="nav-disclaimer">免责声明</a>
        <span class="footer-pipe" aria-hidden="true"></span>
        <a href="#" id="footer-share" class="footer-icon-link" title="分享" aria-label="分享">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><polyline points="16 6 12 2 8 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="2" x2="12" y2="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </a>
        <a href="https://github.com/gz2436/nj-driver-quiz" target="_blank" rel="noopener" class="footer-icon-link" title="GitHub" aria-label="GitHub">
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.1.39-1.99 1.03-2.69-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.69 0 3.84-2.34 4.69-4.57 4.94.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12c0-5.52-4.48-10-10-10z" fill="currentColor"/></svg>
        </a>
        <button type="button" id="footer-theme" class="footer-icon-link" title="切换明暗模式" aria-label="切换明暗模式">
          <svg class="theme-icon-sun" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
          <svg class="theme-icon-moon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </nav>
    </div>
  `;
  document.body.appendChild(footer);
  document.getElementById('footer-disclaimer')?.addEventListener('click', (e) => {
    e.preventDefault();
    const s = loadState();
    showDisclaimer({ ...s, disclaimerAccepted: null }, null);
  });
  document.getElementById('footer-share')?.addEventListener('click', (e) => {
    e.preventDefault();
    shareSite();
  });

  // Theme toggle: cycles light → dark → light. First click = opposite of currently rendered theme.
  const themeBtn = document.getElementById('footer-theme');
  function syncThemeIcon() {
    const isDark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === 'dark'
      : matchMedia('(prefers-color-scheme: dark)').matches;
    themeBtn.classList.toggle('is-dark', isDark);
  }
  syncThemeIcon();
  themeBtn.addEventListener('click', () => {
    const s = loadState();
    const currentlyDark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === 'dark'
      : matchMedia('(prefers-color-scheme: dark)').matches;
    s.theme = currentlyDark ? 'light' : 'dark';
    saveState(s);
    applyTheme(s.theme);
    syncThemeIcon();
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => {
    const s = loadState();
    if (s.theme === 'auto' || !s.theme) syncThemeIcon();
  });
}

function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === 'light' || theme === 'dark') {
    root.dataset.theme = theme;
  } else {
    delete root.dataset.theme;
  }
}

// === Initialize common page elements ===
function initPage(opts = {}) {
  const state = loadState();
  applyLanguage(state.languageDisplay);
  applyTheme(state.theme);
  renderFooter(state);
  ensureDisclaimer(state, opts.onDisclaimerReady);
  return state;
}
