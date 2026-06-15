export async function getItems(limit = 100) {
  const r = await fetch(`/api/items?limit=${limit}`);
  return r.json();
}
export async function getPlaylistMap() {
  const r = await fetch('/api/items/playlist-map');
  return r.json();
}
export async function getVoices() {
  const r = await fetch('/api/voices');
  return r.json();
}
export async function postConvert(body) {
  return fetch('/api/convert', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}
export async function patchProgress(id, position) {
  return fetch(`/api/items/${id}/progress`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ position }) });
}
export async function deleteItem(id) { return fetch(`/api/items/${id}`, { method: 'DELETE' }); }
export async function retryItem(id) { return fetch(`/api/items/${id}/retry`, { method: 'POST' }); }
export async function getPlaylists() { return (await fetch('/api/playlists')).json(); }
export async function createPlaylist(name) { return fetch('/api/playlists', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }); }
export async function deletePlaylist(id) { return fetch(`/api/playlists/${id}`, { method: 'DELETE' }); }
export async function getPlaylistItems(id) { return (await fetch(`/api/playlists/${id}/items`)).json(); }
export async function addItemToPlaylist(pid, itemId) { return fetch(`/api/playlists/${pid}/items`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item_id: itemId }) }); }
export async function removeItemFromPlaylist(pid, itemId) { return fetch(`/api/playlists/${pid}/items/${itemId}`, { method: 'DELETE' }); }
export async function getItemPlaylists(id) { return (await fetch(`/api/items/${id}/playlists`)).json(); }
export async function getToken() { return (await fetch('/api/settings/token')).json(); }
export async function regenerateToken() { return (await fetch('/api/settings/token', { method: 'POST' })).json(); }
