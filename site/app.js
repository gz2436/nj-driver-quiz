// NJ Driver Quiz — Shared JS utilities

const STORAGE_KEY = 'nj_quiz_v1';

const DEFAULT_STATE = {
  version: 1,
  disclaimerAccepted: null,
  wrongAnswers: [],          // question IDs
  bookmarks: [],             // question IDs
  topicProgress: {},         // topic → {seen, correct}
  totalAttempts: 0,
  languageDisplay: 'bilingual',  // 'bilingual' | 'zh' | 'en'
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

function isWeChat() {
  return /MicroMessenger/i.test(navigator.userAgent);
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
  // Find the first Chinese character
  const m = text.match(/[一-鿿]/);
  if (!m) return { en: text.trim(), zh: '' };
  const idx = m.index;
  let en = text.slice(0, idx).trim();
  let zh = text.slice(idx).trim();
  // If the English half is too short, treat as Chinese-only
  if (en.length < 5) return { en: '', zh: text.trim() };
  // Strip trailing punctuation from EN
  en = en.replace(/\s+$/, '');
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
<div class="disclaimer-section">
  <strong>本站为个人学习工具，非新泽西州 MVC（机动车管理委员会）官方网站，也不隶属于任何政府机构、律师事务所或培训机构。</strong>
  <ul>
    <li>题目仅供学习参考，不保证与实际考试相同</li>
    <li>答案以现行 NJ Driver Manual 及 NJ 州法规为准；如有差异以官方为准</li>
    <li>通过本练习不保证通过实际考试</li>
    <li>本站不对题目准确性作任何明示或暗示的担保</li>
    <li>本站不收集任何个人数据，进度仅保存在你的浏览器</li>
    <li>建议同时阅读官方驾驶手册</li>
  </ul>
  <hr>
  <strong>This is a personal study tool, not affiliated with the NJ Motor Vehicle Commission, any government agency, law firm, or training program.</strong>
  <ul>
    <li>Practice questions are for educational reference only</li>
    <li>Answers follow the current NJ Driver Manual and NJ state law; defer to official sources in case of discrepancy</li>
    <li>Passing this practice does NOT guarantee passing the actual exam</li>
    <li>No warranty of any kind, express or implied</li>
    <li>No personal data is collected; progress stays in your browser</li>
    <li>Please also read the official driver manual</li>
  </ul>
</div>
`;

function showDisclaimer(state, onAccept) {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.innerHTML = `
    <div class="modal">
      <h2>免责声明 / Disclaimer</h2>
      ${DISCLAIMER_HTML}
      <div class="modal-actions">
        <button class="btn primary" id="disclaimer-agree">我同意 / I agree</button>
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

// === WeChat banner ===
function setupWechatBanner() {
  if (!isWeChat()) return;
  const banner = document.createElement('div');
  banner.className = 'wechat-banner';
  banner.innerHTML = `
    检测到你在微信中打开。建议点右上角"在浏览器中打开"以获得最佳体验。
    <button title="关闭" id="wechat-close">×</button>
  `;
  document.body.insertBefore(banner, document.body.firstChild);
  document.getElementById('wechat-close').addEventListener('click', () => banner.remove());
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

// === Report error link ===
// Tally form URL — user fills in after creating
const TALLY_FORM_URL = 'https://tally.so/r/REPLACE_ME?qid=';

function reportErrorUrl(questionId) {
  return `${TALLY_FORM_URL}${questionId}`;
}

// === Footer ===
const FOOTER_HTML = `
  <div>
    数据来源：题库初始整理自 <a href="https://www.aiqiang.org/post/nj-driverlicense-written-exam-practice" target="_blank" rel="noopener">aiqiang.org</a>，已与
    <a href="https://www.nj.gov/mvc/pdf/license/drivermanual.pdf" target="_blank" rel="noopener">NJ 官方手册</a> 交叉校验
  </div>
  <div class="links">
    <a href="#" id="footer-disclaimer">免责声明</a>
    <a href="https://github.com/__REPO__" target="_blank" rel="noopener">GitHub 源码</a>
    <a href="https://www.nj.gov/mvc/pdf/license/drivermanual.pdf" target="_blank" rel="noopener">官方手册</a>
    <a href="https://tally.so/r/REPLACE_ME" target="_blank" rel="noopener">报错 / Report</a>
  </div>
  <div class="version">v2026.05.12</div>
`;

function renderFooter() {
  const existing = document.querySelector('footer.site-footer');
  if (existing) return;
  const footer = document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = FOOTER_HTML;
  document.body.appendChild(footer);
  document.getElementById('footer-disclaimer')?.addEventListener('click', (e) => {
    e.preventDefault();
    const state = loadState();
    showDisclaimer({ ...state, disclaimerAccepted: null }, null);
  });
}

// === Initialize common page elements ===
function initPage(opts = {}) {
  const state = loadState();
  applyLanguage(state.languageDisplay);
  setupWechatBanner();
  renderFooter();
  ensureDisclaimer(state, opts.onDisclaimerReady);
  return state;
}
