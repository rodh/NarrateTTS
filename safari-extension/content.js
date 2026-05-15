// Content script: extract page content
function stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    // Get text from body-like elements preferentially
    const selectors = ['article', 'main', '[role="main"]', '.post-content', '.article-body'];
    let content = '';
    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el && el.textContent.length > content.length) {
            content = el.textContent;
        }
    }
    if (!content) {
        content = tmp.textContent || tmp.innerText || '';
    }
    // Clean up whitespace
    return content.replace(/\s+/g, ' ').trim().slice(0, 50000);
}

const title = document.title || '';
const text = stripHtml(document.body?.innerHTML || '');

if (text.length < 100) {
    // Store empty so popup knows extraction failed
    window.__tts_content = null;
} else {
    window.__tts_content = { title, text };
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GET_CONTENT') {
        sendResponse(window.__tts_content);
    }
});
