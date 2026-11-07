/* FootFlex — small progressive-enhancement helpers (everything also works without JS via normal forms). */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  /* ---- toasts ---- */
  const box = $('#toasts');
  const toast = (msg, kind = '') => {
    const t = document.createElement('div');
    t.className = `toast ${kind}`; t.textContent = msg; t.setAttribute('role', 'status');
    box.appendChild(t); setTimeout(() => t.remove(), 3800);
  };
  $$('.toast', box).forEach((t) => setTimeout(() => t.remove(), 4500));

  const setCount = (sel, n) => $$(sel).forEach((el) => { el.textContent = n; el.hidden = !n; });

  /* ---- mobile nav / filters ---- */
  $('#menuBtn')?.addEventListener('click', (e) => {
    const open = $('#nav').classList.toggle('open'); e.currentTarget.setAttribute('aria-expanded', open);
  });
  $('[data-filter-toggle]')?.addEventListener('click', () => $('#filters')?.classList.toggle('open'));
  document.addEventListener('click', (e) => { // close the user menu when clicking elsewhere
    const d = $('.user-menu[open]'); if (d && !d.contains(e.target)) d.removeAttribute('open');
  });



  /* ---- product page: photo thumbnails ---- */
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-thumb]'); if (!b) return;
    const main = $('#mainPhoto'); if (main) main.src = b.dataset.thumb;
    $$('.pd-thumb').forEach((x) => x.classList.toggle('on', x === b));
  });

  /* ---- search popover ---- */
  const sBtn = $('[data-search-toggle]'), sBox = $('#searchBox');
  sBtn?.addEventListener('click', () => {
    const open = sBox.classList.toggle('open'); sBtn.setAttribute('aria-expanded', open);
    if (open) sBox.querySelector('input')?.focus();
  });
  document.addEventListener('click', (e) => { if (sBox?.classList.contains('open') && !sBox.contains(e.target) && !sBtn.contains(e.target)) sBox.classList.remove('open'); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') sBox?.classList.remove('open'); });

  /* ---- colour swatches: recolour the artwork + remember the chosen colour ---- */
  const applyColor = (btn) => {
    const scope = btn.closest('[data-scope]'); if (!scope) return;
    $$('.swatch', scope).forEach((s) => s.classList.toggle('on', s === btn));
    $$('svg.shoe-art', scope).forEach((svg) => { svg.style.cssText = btn.dataset.vars; });
    $$('input[name=color]', scope).forEach((i) => { i.value = btn.dataset.name; });
    $$('[data-color-name]', scope).forEach((el) => { el.textContent = btn.dataset.name; });
  };
  document.addEventListener('click', (e) => { const b = e.target.closest('[data-swatch]'); if (b) applyColor(b); });

  /* ---- ajax forms (cart add, wishlist) ---- */
  document.addEventListener('submit', async (e) => {
    const form = e.target.closest('form[data-ajax]'); if (!form) return;
    if (form.dataset.needSize && !form.elements.size.value) { e.preventDefault(); toast('Please select a size', 'error'); return; }
    e.preventDefault();
    try {
      const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' });
      const data = await res.json();
      if (res.status === 401 && data.login) { toast(data.message, 'error'); setTimeout(() => { location.href = data.login; }, 700); return; }
      toast(data.message, data.ok ? '' : 'error');
      if (data.ok && 'count' in data) {
        if (form.hasAttribute('data-wish')) {
          setCount('[data-wish-count]', data.count);
          $('.wish-btn', form)?.classList.toggle('on', data.on);
          if (!data.on && form.closest('[data-wishlist-page]')) form.closest('.product-card')?.remove();
        } else setCount('[data-cart-count]', data.count);
      }
      if (data.ok && form.hasAttribute('data-quick')) form.classList.remove('open');
    } catch { form.submit(); }
  });

  /* ---- quick add on cards ---- */
  document.addEventListener('click', (e) => {
    const open = e.target.closest('[data-quick-open]');
    if (open) { open.closest('.product-card').querySelector('[data-quick]')?.classList.toggle('open'); return; }
    if (e.target.closest('[data-quick-close]')) { e.target.closest('[data-quick]').classList.remove('open'); return; }
    const sz = e.target.closest('[data-quick] [data-size]');
    if (sz) { const f = sz.closest('form'); f.elements.size.value = sz.dataset.size; f.requestSubmit(); }
  });

  /* ---- hero slider + tilt ---- */
  const slides = $$('.slide');
  if (slides.length) {
    let i = 0, timer; const dots = $$('.dots button');
    const show = (n) => { i = (n + slides.length) % slides.length; slides.forEach((s, k) => s.classList.toggle('on', k === i)); dots.forEach((d, k) => d.classList.toggle('on', k === i)); };
    const auto = () => { clearInterval(timer); if (slides.length > 1) timer = setInterval(() => show(i + 1), 6500); };
    dots.forEach((d, k) => d.addEventListener('click', () => { show(k); auto(); }));
    $('.hero')?.addEventListener('mouseenter', () => clearInterval(timer));
    $('.hero')?.addEventListener('mouseleave', auto);
    auto();
    const stage = $('.stage');
    stage?.addEventListener('pointermove', (e) => {
      const r = stage.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      $$('.stage-shoe', stage).forEach((s) => { s.style.transform = `perspective(900px) rotateY(${x * 14}deg) rotateX(${-y * 10}deg)`; });
    });
    stage?.addEventListener('pointerleave', () => $$('.stage-shoe', stage).forEach((s) => { s.style.transform = ''; }));
  }

  /* ---- product page ---- */
  const pd = $('[data-product-page]');
  if (pd) {
    const form = $('#buyForm');
    $$('.size-btn', pd).forEach((b) => b.addEventListener('click', () => {
      $$('.size-btn', pd).forEach((x) => x.classList.toggle('on', x === b));
      form.elements.size.value = b.dataset.size; $('[data-size-name]').textContent = 'UK ' + b.dataset.size;
      const max = Number(b.dataset.qty); form.elements.qty.max = max; if (Number(form.elements.qty.value) > max) form.elements.qty.value = max;
    }));
    $$('[data-step]', pd).forEach((b) => b.addEventListener('click', () => {
      const q = form.elements.qty; const max = Number(q.max) || 10;
      q.value = Math.min(max, Math.max(1, Number(q.value) + Number(b.dataset.step)));
    }));
    $$('.tabs button', pd).forEach((b) => b.addEventListener('click', () => {
      $$('.tabs button', pd).forEach((x) => x.classList.toggle('on', x === b));
      $$('.tab-panel', pd).forEach((p) => p.classList.toggle('on', p.id === b.dataset.tab));
    }));
    $('[data-guide-open]')?.addEventListener('click', () => $('#sizeGuide').showModal());
    $('[data-guide-close]')?.addEventListener('click', () => $('#sizeGuide').close());
    $('#pinForm')?.addEventListener('submit', (e) => {
      e.preventDefault(); const v = $('#pinInput').value.trim(), out = $('#pinOut');
      if (!/^[1-9]\d{5}$/.test(v)) { out.textContent = 'Enter a valid 6-digit PIN code'; return; }
      const days = ['1', '2', '4', '5', '6'].includes(v[0]) ? 3 : 5; const d = new Date(); d.setDate(d.getDate() + days);
      out.textContent = `Delivery by ${d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })} · Cash on delivery available`;
    });
  }

  /* ---- shop filters: apply instantly ---- */
  const ff = $('#filters');
  if (ff) {
    ff.addEventListener('change', () => ff.submit());
    $('#sortSelect')?.addEventListener('change', (e) => { ff.elements.sort.value = e.target.value; ff.submit(); });
    const range = $('#maxRange'); range?.addEventListener('input', () => { $('#maxOut').textContent = '₹' + Number(range.value).toLocaleString('en-IN'); });
  }

  /* ---- checkout ---- */
  const pay = $$('input[name=method]');
  if (pay.length) {
    const sync = () => { const v = pay.find((p) => p.checked)?.value; $$('.pay-extra').forEach((x) => x.classList.toggle('on', x.dataset.for === v)); };
    pay.forEach((p) => p.addEventListener('change', sync)); sync();
    $('#cardNo')?.addEventListener('input', (e) => { e.target.value = e.target.value.replace(/\D/g, '').slice(0, 19).replace(/(.{4})/g, '$1 ').trim(); });
    $('#cardExp')?.addEventListener('input', (e) => { let v = e.target.value.replace(/\D/g, '').slice(0, 4); if (v.length > 2) v = v.slice(0, 2) + '/' + v.slice(2); e.target.value = v; });
  }

  /* ---- dashboard product form ---- */
  const cat = $('#id_category');
  if (cat && $$('.stock-group').length) {
    const sync = () => $$('.stock-group').forEach((g) => g.classList.toggle('on', g.dataset.cat === cat.value));
    cat.addEventListener('change', sync); sync();
  }
  $('#id_image')?.addEventListener('change', (e) => {
    const f = e.target.files[0]; const img = $('#imgPreview'); if (f && img) { img.src = URL.createObjectURL(f); img.hidden = false; }
  });
  $$('[data-confirm]').forEach((f) => f.addEventListener('submit', (e) => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));
})();
