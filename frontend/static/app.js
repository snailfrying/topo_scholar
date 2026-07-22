const state = {
  dataset: 'knowledge',
  offset: 0,
  limit: 10,
  total: 0,
  summary: null,
  mapItems: [],
};

const nodes = {
  statsGrid: document.querySelector('#statsGrid'),
  keyword: document.querySelector('#keywordInput'),
  dataset: document.querySelector('#datasetSelect'),
  level: document.querySelector('#levelSelect'),
  placeType: document.querySelector('#placeTypeSelect'),
  sourceType: document.querySelector('#sourceTypeSelect'),
  confidence: document.querySelector('#confidenceSelect'),
  status: document.querySelector('#statusSelect'),
  province: document.querySelector('#provinceSelect'),
  limit: document.querySelector('#limitSelect'),
  resultList: document.querySelector('#resultList'),
  resultCount: document.querySelector('#resultCount'),
  resultsTitle: document.querySelector('#resultsTitle'),
  pageInfo: document.querySelector('#pageInfo'),
  prev: document.querySelector('#prevButton'),
  next: document.querySelector('#nextButton'),
  backTop: document.querySelector('#backTopButton'),
  search: document.querySelector('#searchButton'),
  reset: document.querySelector('#resetButton'),
  refresh: document.querySelector('#refreshButton'),
  map: document.querySelector('#chinaMap'),
  mapDetail: document.querySelector('#mapDetail'),
};

const titles = {
  knowledge: '名字由来知识',
  places: '全部基础地名',
  queue: '采集队列',
};

function formatNumber(value) {
  return new Intl.NumberFormat('zh-CN').format(Number(value || 0));
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

async function fetchJson(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  const response = await fetch(url);
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

function option(label, value) {
  const item = document.createElement('option');
  item.value = value;
  item.textContent = label;
  return item;
}

function fillSelect(select, rows, labelKey, valueKey = labelKey) {
  const first = select.firstElementChild?.cloneNode(true);
  select.replaceChildren();
  if (first) select.append(first);
  rows.forEach((row) => select.append(option(row[labelKey] || '未标注', row[valueKey] || '')));
}

function renderStats(summary) {
  const counts = summary.counts || {};
  const queue = summary.queueStatus || {};
  const cards = [
    ['基础地名', counts.places, '五级行政地名底座'],
    ['名字由来', counts.place_knowledge, '已结构化记录'],
    ['别名索引', counts.place_aliases, '消歧与模糊查询'],
    ['街道试点', queue.done, `完成，${formatNumber(queue.needs_review)} 待复核`],
  ];
  nodes.statsGrid.replaceChildren(
    ...cards.map(([label, value, hint]) => {
      const card = document.createElement('article');
      card.className = 'stat-card';
      card.innerHTML = `<span>${label}</span><strong>${formatNumber(value)}</strong><small>${hint}</small>`;
      return card;
    }),
  );
}

function renderFilters(summary) {
  fillSelect(nodes.province, summary.provinces || [], 'province');
  fillSelect(nodes.placeType, summary.knowledgeTypes || [], 'place_type');
  fillSelect(nodes.sourceType, summary.sourceTypes || [], 'source_type');
  fillSelect(nodes.confidence, summary.confidence || [], 'confidence');
}

function syncDatasetFields() {
  state.dataset = nodes.dataset.value;
  document.body.dataset.dataset = state.dataset;
  nodes.resultsTitle.textContent = titles[state.dataset];
}

function buildParams() {
  const params = {
    dataset: state.dataset,
    q: nodes.keyword.value.trim(),
    province: nodes.province.value,
    limit: nodes.limit.value,
    offset: state.offset,
  };
  if (state.dataset === 'places') params.level = nodes.level.value;
  if (state.dataset === 'knowledge') {
    params.place_type = nodes.placeType.value;
    params.source_type = nodes.sourceType.value;
    params.confidence = nodes.confidence.value;
  }
  if (state.dataset === 'queue') params.status = nodes.status.value;
  return params;
}

function badge(text, tone = 'neutral') {
  return `<span class="badge ${tone}">${escapeHtml(text || '未标注')}</span>`;
}

function compactText(value, max = 180) {
  if (!value) return '';
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

function fieldBlock(label, value, max = 2000) {
  if (!value) return '';
  return `
    <div class="knowledge-field">
      <span>${label}</span>
      <p>${escapeHtml(compactText(value, max))}</p>
    </div>
  `;
}

function renderKnowledge(item) {
  const summary = item.origin || item.meaning || item.history || '暂无摘要';
  const hasMore = item.old_names || item.evidence_title || item.evidence_url;
  return `
    <article class="result-card knowledge-card">
      <div class="card-head">
        <div><strong>${escapeHtml(item.standard_name)}</strong><span>${escapeHtml(item.local_full_name || item.province || '')}</span></div>
        ${badge(item.confidence, item.confidence === 'high' ? 'good' : 'warn')}
      </div>
      ${fieldBlock('由来摘要', summary)}
      ${fieldBlock('名称含义', item.meaning)}
      ${fieldBlock('历史沿革', item.history)}
      ${
        hasMore
          ? `<details class="knowledge-details">
              <summary>旧称与来源</summary>
              ${fieldBlock('旧称', item.old_names, 180)}
              ${fieldBlock('证据来源', item.evidence_title || item.evidence_url, 220)}
            </details>`
          : ''
      }
      <div class="meta-line">
        ${badge(item.place_type)} ${badge(item.source_type)} ${item.local_code ? badge(item.local_code, 'code') : ''}
      </div>
    </article>`;
}

function renderPlace(item) {
  return `
    <article class="result-card">
      <div class="card-head">
        <div><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.full_name)}</span></div>
        ${badge(item.level, 'code')}
      </div>
      <div class="meta-line">
        ${badge(item.code, 'code')} ${badge(item.type)} ${item.parent_code ? badge(`上级 ${item.parent_code}`) : ''}
      </div>
    </article>`;
}

function renderQueue(item) {
  const tone = item.status === 'done' ? 'good' : item.status === 'needs_review' ? 'warn' : 'neutral';
  return `
    <article class="result-card">
      <div class="card-head">
        <div><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.full_name)}</span></div>
        ${badge(item.status, tone)}
      </div>
      <div class="meta-line">
        ${badge(item.code, 'code')} ${badge(item.collection_phase)} ${item.error ? badge(item.error, 'warn') : ''}
      </div>
    </article>`;
}

function renderResults(payload) {
  state.total = payload.total || 0;
  state.limit = payload.limit || Number(nodes.limit.value);
  const items = payload.items || [];
  const renderers = { knowledge: renderKnowledge, places: renderPlace, queue: renderQueue };
  nodes.resultList.innerHTML = items.length
    ? items.map(renderers[state.dataset]).join('')
    : document.querySelector('#emptyTemplate').innerHTML;
  nodes.resultCount.textContent = `${formatNumber(state.total)} 条`;
  const currentPage = Math.floor(state.offset / state.limit) + 1;
  const pageCount = Math.max(1, Math.ceil(state.total / state.limit));
  nodes.pageInfo.textContent = `${currentPage} / ${pageCount}`;
  nodes.prev.disabled = state.offset <= 0;
  nodes.next.disabled = state.offset + state.limit >= state.total;
}

async function runSearch({ resetOffset = false } = {}) {
  if (resetOffset) state.offset = 0;
  syncDatasetFields();
  nodes.resultList.innerHTML = '<div class="loading">正在读取本地数据…</div>';
  const payload = await fetchJson('/api/search', buildParams());
  renderResults(payload);
}

function scrollToResultsTop() {
  document.querySelector('.results')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function projectPoint(item, bounds, width, height) {
  const x = ((item.lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * width;
  const y = height - ((item.lat - bounds.minLat) / (bounds.maxLat - bounds.minLat)) * height;
  return [x, y];
}

function renderMap(payload) {
  state.mapItems = payload.items || [];
  const width = 820;
  const height = 520;
  const maxKnowledge = Math.max(...state.mapItems.map((item) => item.knowledge), 1);
  nodes.map.setAttribute('viewBox', `0 0 ${width} ${height}`);
  nodes.map.replaceChildren();

  const grid = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  grid.setAttribute('class', 'map-grid');
  for (let i = 0; i < 8; i += 1) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', '0');
    line.setAttribute('x2', String(width));
    line.setAttribute('y1', String(40 + i * 56));
    line.setAttribute('y2', String(40 + i * 56));
    grid.append(line);
  }
  nodes.map.append(grid);

  state.mapItems.forEach((item) => {
    const [x, y] = projectPoint(item, payload.bounds, width, height);
    const radius = 7 + Math.sqrt(item.knowledge / maxKnowledge) * 28;
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'province-dot');
    group.setAttribute('tabindex', '0');
    group.setAttribute('transform', `translate(${x.toFixed(1)} ${y.toFixed(1)})`);
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    circle.setAttribute('r', radius.toFixed(1));
    label.setAttribute('y', String(radius + 15));
    label.setAttribute('text-anchor', 'middle');
    label.textContent = item.province.replace('自治区', '').replace('省', '').replace('市', '');
    group.append(circle, label);
    group.addEventListener('click', () => selectProvince(item));
    group.addEventListener('mouseenter', () => updateMapDetail(item));
    nodes.map.append(group);
  });
}

function updateMapDetail(item) {
  nodes.mapDetail.innerHTML = `
    <strong>${escapeHtml(item.province)}</strong>
    <span>基础地名 ${formatNumber(item.places)} 条</span>
    <span>由来知识 ${formatNumber(item.knowledge)} 条</span>
  `;
}

function selectProvince(item) {
  nodes.province.value = item.province;
  updateMapDetail(item);
  runSearch({ resetOffset: true });
}

async function boot() {
  state.summary = await fetchJson('/api/summary');
  renderStats(state.summary);
  renderFilters(state.summary);
  renderMap(await fetchJson('/api/map'));
  syncDatasetFields();
  await runSearch({ resetOffset: true });
}

nodes.dataset.addEventListener('change', () => runSearch({ resetOffset: true }));
nodes.search.addEventListener('click', () => runSearch({ resetOffset: true }));
nodes.reset.addEventListener('click', () => {
  document.querySelectorAll('input, select').forEach((node) => {
    if (node.id === 'datasetSelect') node.value = 'knowledge';
    else if (node.id === 'limitSelect') node.value = '10';
    else node.value = '';
  });
  runSearch({ resetOffset: true });
});
nodes.refresh.addEventListener('click', boot);
nodes.keyword.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') runSearch({ resetOffset: true });
});
[nodes.level, nodes.placeType, nodes.sourceType, nodes.confidence, nodes.status, nodes.province, nodes.limit].forEach((node) => {
  node.addEventListener('change', () => runSearch({ resetOffset: true }));
});
nodes.prev.addEventListener('click', () => {
  state.offset = Math.max(0, state.offset - state.limit);
  runSearch().then(scrollToResultsTop);
});
nodes.next.addEventListener('click', () => {
  state.offset += state.limit;
  runSearch().then(scrollToResultsTop);
});
nodes.backTop.addEventListener('click', scrollToResultsTop);

boot().catch((error) => {
  nodes.resultList.innerHTML = `<div class="empty-state"><strong>前端启动失败</strong><span>${error.message}</span></div>`;
});
