(function(){
  function ensureContainer(){
    let c = document.getElementById('app-notice-container');
    if (c) return c;
    c = document.createElement('div');
    c.id = 'app-notice-container';
    c.style.position = 'fixed';
    c.style.top = '10px';
    c.style.left = '50%';
    c.style.transform = 'translateX(-50%)';
    c.style.zIndex = '9999';
    c.style.maxWidth = '90%';
    c.style.pointerEvents = 'none';
    document.body.appendChild(c);
    return c;
  }

  function makeBanner(text, kind){
    const banner = document.createElement('div');
    banner.setAttribute('role', 'alert');
    banner.style.pointerEvents = 'auto';
    banner.style.margin = '6px auto';
    banner.style.padding = '10px 14px';
    banner.style.borderRadius = '6px';
    banner.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
    banner.style.fontFamily = 'Arial, sans-serif';
    banner.style.fontSize = '14px';
    banner.style.border = '1px solid';
    if (kind === 'error'){
      banner.style.background = '#fdecea';
      banner.style.color = '#611a15';
      banner.style.borderColor = '#f5c6cb';
    } else {
      banner.style.background = '#fff3cd';
      banner.style.color = '#856404';
      banner.style.borderColor = '#ffeeba';
    }
    banner.textContent = text;
    // close button
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = '×';
    close.style.marginLeft = '8px';
    close.style.border = 'none';
    close.style.background = 'transparent';
    close.style.cursor = 'pointer';
    close.style.fontSize = '16px';
    close.setAttribute('aria-label', 'Dismiss');
    close.onclick = function(e){ e.stopPropagation(); banner.remove(); };
    banner.appendChild(close);
    return banner;
  }

  function show(kind, text, autoHideMs){
    const c = ensureContainer();
    const b = makeBanner(text || (kind==='error' ? 'Something went wrong.' : 'Warning: Something may be wrong.'), kind);
    c.appendChild(b);
    if (autoHideMs){
      setTimeout(() => { try { b.remove(); } catch(_){} }, autoHideMs);
    }
    return b;
  }

  window.AppNotice = {
    warn: function(text, autoHideMs){ return show('warn', text, autoHideMs || 6000); },
    error: function(text, autoHideMs){ return show('error', text, autoHideMs || 8000); },
    clear: function(){ const c = document.getElementById('app-notice-container'); if (c) c.innerHTML = ''; }
  };
})();
