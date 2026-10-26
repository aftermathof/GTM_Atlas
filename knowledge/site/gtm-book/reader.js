(() => {
  const $ = selector => document.querySelector(selector);
  const searchDialog = $('#search-dialog');
  const imageDialog = $('#image-dialog');
  const input = $('#book-search');
  const results = $('#search-results');
  const status = $('#search-status');
  const index = window.GTM_BOOK_SEARCH || [];
  if($('.book-body') && window.renderMathInElement) window.renderMathInElement($('.book-body'), {delimiters:[{left:'$',right:'$',display:false}],throwOnError:false});
  $('#search-open').addEventListener('click', () => { searchDialog.showModal(); input.focus(); });
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  [searchDialog, imageDialog].forEach(dialog => dialog.addEventListener('click', event => { if (event.target === dialog) { const box = dialog.getBoundingClientRect(); if(event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close(); } }));
  function highlight(container, text, query) {
    const start = text.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
    if(start < 0) { container.textContent = text; return; }
    container.append(document.createTextNode(text.slice(0,start)));
    const mark = document.createElement('mark'); mark.textContent = text.slice(start,start+query.length); container.append(mark,document.createTextNode(text.slice(start+query.length)));
  }
  let searchTimer;
  input.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const query = input.value.trim(); results.replaceChildren();
      if(!query) { status.textContent = '输入关键词，查找六章正文与附录。'; return; }
      const lower = query.toLocaleLowerCase();
      const hits = index.filter(item => item.text.toLocaleLowerCase().includes(lower));
      status.textContent = `找到 ${hits.length} 处匹配${hits.length > 60 ? '，先显示前 60 处，请添加关键词缩小范围' : ''}。`;
      hits.slice(0,60).forEach(item => {
        const row = document.createElement('li'), link = document.createElement('a'), chapter = document.createElement('span'), title = document.createElement('h3'), snippet = document.createElement('p');
        link.href = item.href; chapter.className = 't-meta'; chapter.textContent = item.chapter; title.textContent = item.title;
        const position = item.text.toLocaleLowerCase().indexOf(lower), start = Math.max(0,position-32);
        const text = (start ? '…' : '')+item.text.slice(start,start+150)+(item.text.length > start+150 ? '…' : '');
        highlight(snippet,text,query); link.append(chapter,title,snippet); row.append(link); results.append(row);
      });
    }, 120);
  });
  function openImage(image) { $('#large-image').src = image.src; $('#large-image').alt = image.alt; $('#image-original').href = image.src; imageDialog.showModal(); }
  document.querySelectorAll('article img').forEach(image => {
    image.addEventListener('click', () => openImage(image));
    image.addEventListener('keydown', event => { if(event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openImage(image); } });
  });
  $('#menu-toggle').addEventListener('click', () => { const open = document.body.classList.toggle('menu-open'); $('#menu-toggle').setAttribute('aria-expanded',String(open)); });
  document.querySelectorAll('.local-toc a').forEach(link => link.addEventListener('click', () => { document.body.classList.remove('menu-open'); $('#menu-toggle').setAttribute('aria-expanded','false'); }));
  // Storage is optional: reading still works in private or restricted browser contexts.
  const storageKey = 'gtm-book-reading-v1';
  try {
    const previous = JSON.parse(localStorage.getItem(storageKey) || 'null');
    if(document.body.dataset.page === '0' && previous && /^chapter-0[1-7]\.html(?:#section-\d+)?$/.test(previous.href)) { const resume = $('#resume-reading'); resume.href = previous.href; resume.hidden = false; }
    if(document.body.dataset.page !== '0') {
      const pageName = location.pathname.split('/').pop();
      const save = () => {
        const headings = [...document.querySelectorAll('article h1,article h2,article h3')];
        const current = headings.filter(heading => heading.getBoundingClientRect().top <= 130).pop() || headings[0];
        try { localStorage.setItem(storageKey,JSON.stringify({href:pageName+(current ? '#'+current.id : '')})); } catch {}
      };
      let timer; window.addEventListener('scroll', () => { clearTimeout(timer); timer=setTimeout(save,300); }, {passive:true}); window.addEventListener('pagehide',save);
    }
  } catch {}
})();
