/* boootie.com behaviour: no framework, no dependencies.
   - draw-in of doodles when their section enters the viewport
   - sticky bottom CTA on mobile once the hero CTA scrolls away
   - Stripe link passthrough (client_reference_id + utm_*)
   - privacy-friendly analytics events
   - FAQ open tracking, email signup form
   - lazy <model-viewer> with a static poster
   - headline variant preview via ?h=1|2 */
(function () {
  'use strict';
  const doc = document;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, r) => (r || doc).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || doc).querySelectorAll(s));

  /* ---------- analytics (Vercel Web Analytics, custom events) ---------- */
  function track(name, data) {
    try {
      if (window.va) window.va('event', { name: name, data: data || {} });
      else if (window.plausible) window.plausible(name, { props: data || {} });
    } catch (e) { /* analytics must never break the page */ }
  }

  /* ---------- traffic source -> Stripe passthrough ---------- */
  const params = new URLSearchParams(location.search);
  const KEY = 'boootie_src';
  const utm = {};
  ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'ref'].forEach(function (k) {
    if (params.get(k)) utm[k] = params.get(k);
  });
  try {
    if (Object.keys(utm).length) sessionStorage.setItem(KEY, JSON.stringify(utm));
    else Object.assign(utm, JSON.parse(sessionStorage.getItem(KEY) || '{}'));
  } catch (e) { /* storage may be unavailable */ }
  function refId() {
    const src = utm.utm_source || utm.ref || 'direct';
    const parts = [src, utm.utm_campaign, utm.utm_content].filter(Boolean).join('_');
    return parts.replace(/[^A-Za-z0-9_-]/g, '-').slice(0, 180);
  }
  function decorate(a) {
    try {
      const u = new URL(a.href);
      u.searchParams.set('client_reference_id', refId());
      Object.keys(utm).forEach(function (k) { if (k.indexOf('utm_') === 0) u.searchParams.set(k, utm[k]); });
      a.href = u.toString();
    } catch (e) { /* leave the link alone */ }
  }
  $$('a[data-cta]').forEach(function (a) {
    decorate(a);
    a.addEventListener('click', function () { track('cta_click', { placement: a.getAttribute('data-cta'), source: utm.utm_source || 'direct' }); });
  });

  /* ---------- headline variant preview: ?h=1 or ?h=2 ---------- */
  const h1 = $('#headline');
  const hv = parseInt(params.get('h'), 10);
  if (h1 && hv >= 0) {
    try { const list = JSON.parse(h1.getAttribute('data-headlines') || '[]'); if (list[hv]) h1.innerHTML = list[hv]; } catch (e) { /* ignore */ }
  }

  /* ---------- desktop hero field (kept out of the mobile DOM) ---------- */
  const tpl = $('#field-d');
  if (tpl && matchMedia('(min-width: 768px)').matches) tpl.parentNode.insertBefore(tpl.content.cloneNode(true), tpl);

  /* ---------- draw-in on view ---------- */
  doc.documentElement.classList.replace('no-js', 'js');
  const pending = $$('.pending');
  if (reduced || !('IntersectionObserver' in window)) {
    pending.forEach(function (el) { el.classList.remove('pending'); });
  } else {
    const hero = $('.hero');
    requestAnimationFrame(function () { requestAnimationFrame(function () { $$('.pending', hero).forEach(function (el) { el.classList.remove('pending'); }); }); });
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.remove('pending'); io.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.15 });
    pending.forEach(function (el) { if (!hero.contains(el)) io.observe(el); });
  }

  /* ---------- sticky CTA (mobile) ---------- */
  const bar = $('#sticky-cta');
  const heroCta = $('#hero-cta');
  const preorderCta = $('#preorder-cta');
  if (bar && heroCta && 'IntersectionObserver' in window) {
    const vis = { hero: true, pre: false };
    const update = function () {
      const show = !vis.hero && !vis.pre && window.scrollY > 200;
      bar.classList.toggle('show', show);
      doc.documentElement.classList.toggle('has-sticky', show);
      bar.setAttribute('aria-hidden', show ? 'false' : 'true');
      $$('a, button', bar).forEach(function (el) { el.tabIndex = show ? 0 : -1; });
    };
    const io2 = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.target === heroCta) vis.hero = en.isIntersecting; if (en.target === preorderCta) vis.pre = en.isIntersecting; });
      update();
    }, { threshold: 0.1 });
    io2.observe(heroCta);
    if (preorderCta) io2.observe(preorderCta);
    update();
  }

  /* ---------- FAQ: tracking + deep links (#q-...) ---------- */
  $$('.faq details').forEach(function (d) {
    d.addEventListener('toggle', function () {
      if (!d.open) return;
      track('faq_open', { question: ($('summary', d).textContent || '').trim().slice(0, 80) });
      if (d.id) history.replaceState(null, '', '#' + d.id);
    });
  });
  if (location.hash && /^#q-/.test(location.hash)) { const d = $(location.hash); if (d && d.tagName === 'DETAILS') { d.open = true; } }

  /* ---------- pause / play motion (the loops run longer than 5 seconds) ---------- */
  const mt = $('#motion-toggle');
  if (mt) {
    let still = false;
    try { still = localStorage.getItem('boootie_still') === '1'; } catch (e) { /* ignore */ }
    const apply = function () {
      doc.documentElement.classList.toggle('still', still);
      mt.setAttribute('aria-pressed', still ? 'true' : 'false');
      mt.textContent = still ? 'Play motion' : 'Pause motion';
      const mv = $('model-viewer'); if (mv) { if (still) mv.removeAttribute('auto-rotate'); else if (!reduced) mv.setAttribute('auto-rotate', ''); }
    };
    mt.addEventListener('click', function () { still = !still; try { localStorage.setItem('boootie_still', still ? '1' : '0'); } catch (e) { /* ignore */ } apply(); });
    apply();
    window.__boootieStill = function () { return still; };
  }

  /* ---------- email signup (Formspree) ---------- */
  const form = $('#signup');
  if (form) {
    const note = $('#signup-note');
    const btn = $('button[type=submit]', form);
    const say = function (msg, ok) { note.hidden = false; note.textContent = msg; note.setAttribute('data-state', ok ? 'ok' : 'error'); };
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      const email = $('#email', form);
      if (!form.checkValidity()) { say('Enter an email address, like name@example.com.', false); email.setAttribute('aria-invalid', 'true'); email.focus(); return; }
      email.removeAttribute('aria-invalid');
      const data = new FormData(form);
      btn.disabled = true; btn.textContent = 'Sending…';
      fetch(form.action, { method: 'POST', body: data, headers: { Accept: 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(r); })
        .then(function () { form.reset(); say("You're on the list. We'll email you when there's news.", true); track('email_signup', { source: utm.utm_source || 'direct' }); })
        .catch(function () { say("That didn't go through. Email " + (form.getAttribute('data-support') || 'us') + " and we'll add you by hand.", false); })
        .then(function () { btn.disabled = false; btn.textContent = btn.getAttribute('data-label'); });
    });
  }

  /* ---------- 3D model: lazy, after first paint, with poster ---------- */
  const box = $('#model');
  if (box && !(navigator.connection && navigator.connection.saveData)) {
    const start = function () {
      if (box.getAttribute('data-loaded')) return;
      box.setAttribute('data-loaded', '1');
      const s = doc.createElement('script');
      s.type = 'module';
      s.src = 'https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js';
      s.onload = function () {
        const mv = doc.createElement('model-viewer');
        mv.setAttribute('src', box.getAttribute('data-src'));
        mv.setAttribute('poster', box.getAttribute('data-poster'));
        mv.setAttribute('alt', box.getAttribute('data-alt') || '');
        mv.setAttribute('camera-controls', '');
        mv.setAttribute('disable-zoom', '');
        mv.setAttribute('disable-pan', '');
        mv.setAttribute('interaction-prompt', 'none');
        mv.setAttribute('touch-action', 'pan-y');
        mv.setAttribute('shadow-intensity', '1.2');
        mv.setAttribute('shadow-softness', '0.9');
        mv.setAttribute('exposure', '0.9');
        mv.setAttribute('environment-image', 'neutral');
        mv.setAttribute('camera-orbit', '38deg 68deg 140%');
        mv.setAttribute('min-camera-orbit', 'auto 40deg auto');
        mv.setAttribute('max-camera-orbit', 'auto 100deg auto');
        mv.setAttribute('field-of-view', '22deg');
        if (!reduced && !(window.__boootieStill && window.__boootieStill())) { mv.setAttribute('auto-rotate', ''); }
        mv.setAttribute('auto-rotate-delay', '0'); mv.setAttribute('rotation-per-second', '14deg');
        mv.addEventListener('load', function () { box.setAttribute('data-ready', '1'); track('model_loaded'); });
        box.replaceChildren(mv);
      };
      doc.head.appendChild(s);
    };
    const go = function () { if ('requestIdleCallback' in window) requestIdleCallback(start, { timeout: 4000 }); else setTimeout(start, 1500); };
    const conn = navigator.connection;
    const slow = conn && (conn.saveData || /2g/.test(conn.effectiveType || ''));
    if (!slow) {
      // first sign of a person (scroll, touch, pointer, key) starts the viewer; a late timer covers the rest
      let armed = false;
      const once = function () { if (armed) return; armed = true; go(); };
      ['scroll', 'pointermove', 'touchstart', 'keydown', 'pointerdown'].forEach(function (ev) { window.addEventListener(ev, once, { once: true, passive: true }); });
      window.addEventListener('load', function () { setTimeout(once, 12000); }, { once: true });
    }
  }
})();
