// Deterministic source-derived art with og:image override.
function domainOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
}
function hashStr(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }

export function faviconUrl(sourceUrl) {
  const d = domainOf(sourceUrl);
  return d ? `https://www.google.com/s2/favicons?domain=${d}&sz=64` : '';
}

const PALETTES = [
  ['#f1582c', '#b51d6e'], ['#2563eb', '#06b6d4'], ['#16a34a', '#84cc16'],
  ['#7c3aed', '#ec4899'], ['#0891b2', '#3b82f6'], ['#ea580c', '#facc15'],
];
export function gradientFor(sourceUrl) {
  const [a, b] = PALETTES[hashStr(domainOf(sourceUrl) || 'text') % PALETTES.length];
  return `linear-gradient(135deg, ${a}, ${b})`;
}

export function letterFor(item) {
  const d = domainOf(item.source_url || '');
  return (d ? d[0] : (item.title || '?')[0]).toUpperCase();
}

// Returns an HTML string for a square art tile of the given pixel size.
export function itemArt(item, size = 44) {
  const r = Math.round(size * 0.27);
  if (item.image_url) {
    return `<div style="width:${size}px;height:${size}px;border-radius:${r}px;background:url('${item.image_url}') center/cover;flex:0 0 auto"></div>`;
  }
  const fav = faviconUrl(item.source_url || '');
  const favHtml = fav ? `<img src="${fav}" style="width:18px;height:18px;border-radius:5px" onerror="this.style.display='none'">` : '';
  return `<div style="width:${size}px;height:${size}px;border-radius:${r}px;background:${gradientFor(item.source_url || '')};display:flex;align-items:center;justify-content:center;flex:0 0 auto">${favHtml || `<span style="color:#fff;font-weight:700">${letterFor(item)}</span>`}</div>`;
}
