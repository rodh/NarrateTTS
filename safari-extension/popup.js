const statusEl = document.getElementById('status');
const btn = document.getElementById('convert-btn');

// Get content from the active tab
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) return;
    chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_CONTENT' }, (response) => {
        if (chrome.runtime.lastError || !response) {
            document.getElementById('title').textContent = 'Could not read this page';
            document.getElementById('meta').textContent = 'Try refreshing and clicking again';
            btn.disabled = true;
            return;
        }
        document.getElementById('title').textContent = response.title;
        const words = (response.text || '').split(/\s+/).length;
        const mins = Math.max(1, Math.ceil(words / 150));
        document.getElementById('meta').textContent = `${words.toLocaleString()} words · ~${mins} min`;
        // Store content for conversion
        window._tts_content = response;
    });
});

async function convert() {
    if (!window._tts_content) return;
    btn.disabled = true;
    statusEl.textContent = 'Converting...';
    statusEl.className = 'status';

    try {
        const result = await fetch('http://lumi.lab:8090/api/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: window._tts_content.text })
        });
        const data = await result.json();
        statusEl.textContent = `Saved to library!`;
        setTimeout(() => { statusEl.textContent = ''; }, 3000);
    } catch (e) {
        statusEl.textContent = 'Failed: is the server running?';
        statusEl.className = 'status error';
        btn.disabled = false;
    }
}
        if (!response) {
            document.getElementById('title').textContent = 'Could not read this page';
            document.getElementById('meta').textContent = 'Try right-clicking the extension icon -> "Save to Audio"';
            return;
        }
        document.getElementById('title').textContent = response.title;
        const words = (response.text || '').split(/\s+/).length;
        const mins = Math.max(1, Math.ceil(words / 150));
        document.getElementById('meta').textContent = `${words.toLocaleString()} words · ~${mins} min`;
    });
});

async function convert() {
    btn.disabled = true;
    statusEl.textContent = 'Converting...';
    statusEl.className = 'status';

    const title = document.getElementById('title').textContent;
    const text = document.getElementById('meta').textContent;

    // Get content again (it's in the content script scope)
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
        try {
            const response = await chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_CONTENT' });
            const result = await fetch('http://lumi.lab:8090/api/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: response.text })
            });
            const data = await result.json();
            statusEl.textContent = `Saved! (${data.id})`;
            setTimeout(() => { statusEl.textContent = ''; }, 3000);
        } catch (e) {
            statusEl.textContent = 'Failed: is the server running?';
            statusEl.className = 'status error';
        } finally {
            btn.disabled = false;
        }
    });
}
