(async function() {
  initPage();
  document.getElementById('back-btn').addEventListener('click', () => { location.href = 'index.html'; });
  const ex = await fetchData('../data/explanations.json');

  // Strip bilingual English companion text, keep abbreviations (≤3 ASCII letters: NJ, BAC, DUI, GDL, IID, mph, ft, oz, yr ...)
  function toCN(s) {
    if (typeof s !== 'string') return s;
    if (!/[一-鿿]/.test(s)) return s;
    // Split by ideographic full-width space — bilingual pair separator (Chinese first)
    if (s.includes('　')) {
      const parts = s.split('　');
      const cjk = parts.filter(p => /[一-鿿]/.test(p));
      if (cjk.length > 0) return cjk[0].trim();
    }
    // Token-level: drop pure-ASCII-letter tokens of length >= 4 (Adult, Octagon, STOP, YIELD ...)
    return s.split(/\s+/).filter(t => !/^[A-Za-z]{4,}$/.test(t)).join(' ').trim();
  }

  // Curated section order — most-tested topics first
  const sections = [
    { keys: ['adult_bac', 'under21_bac'],                                                        title: 'BAC 限值　BAC' },
    { keys: ['alcohol_equivalent'],                                                              title: '酒精等量' },
    { keys: ['dui_first_offense', 'dui_second_offense', 'dui_third_offense', 'dui_refusal'],     title: 'DUI 处罚' },
    { keys: ['park_fire_hydrant'],                                                               title: '停车距离' },
    { keys: ['speed_points'],                                                                    title: '超速扣分' },
    { keys: ['speed_limits'],                                                                    title: '默认限速' },
    { keys: ['tailgating_points'],                                                               title: '移动违规扣分' },
    { keys: ['stopping_distance'],                                                               title: '制动距离' },
    { keys: ['gdl_age_summary', 'gdl_decal', 'gdl_practice'],                                    title: 'GDL 阶段' },
    { keys: ['address_change'],                                                                  title: 'MVC 报告时限' },
    { keys: ['inspection_freq'],                                                                 title: '车辆检查' },
    { keys: ['uninsured'],                                                                       title: '无保险驾车' },
    { keys: ['flashing_red_signal'],                                                             title: '闪烁信号灯' },
    { keys: ['school_bus_stopped'],                                                              title: '校车停车' },
    { keys: ['follow_distance'],                                                                 title: '跟车距离' },
    { keys: ['headlight_use'],                                                                   title: '车灯使用' },
    { keys: ['hill_parking_wheels'],                                                             title: '坡道停车' },
    { keys: ['seat_belt_law'],                                                                   title: '安全带与儿童座椅' },
    { keys: ['hand_signals'],                                                                    title: '手势信号' },
    { keys: ['sign_shapes', 'sign_colors'],                                                      title: '标志形状与颜色' },
  ];

  const grid = document.getElementById('cheatsheet-grid');
  const seen = new Set();

  for (const section of sections) {
    // Pick first key that exists AND has a card; dedup by card title
    let card = null;
    for (const k of section.keys) {
      const e = ex[k];
      if (e && e.card && !seen.has(e.card.title)) {
        card = e.card;
        seen.add(card.title);
        break;
      }
    }
    if (!card) continue;
    const div = document.createElement('div');
    div.className = 'cheat-block';
    const rows = card.rows.map(r => `<tr><td>${toCN(r[0])}</td><td>${toCN(r[1])}</td></tr>`).join('');
    div.innerHTML = `
      <div class="cheat-title">${toCN(card.title)}</div>
      <table>${rows}</table>
    `;
    grid.appendChild(div);
  }
})();
