// content.js

async function executeCommand(command) {
  const { type, payload } = command;

  if (type === "OPEN_URL") {
    if (payload && payload.url) {
      window.location.href = payload.url;
    }
  }

  if (type === "FILL_SELECTOR") {
    // payload: { selector: "input[name='email']", value: "test@example.com" }
    try {
      const el = document.querySelector(payload.selector);
      if (el) {
        el.focus();
        el.value = payload.value;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } catch (e) {
      console.error("FILL_SELECTOR error", e);
    }
  }

  if (type === "CLICK_SELECTOR") {
    // payload: { selector: "button[type='submit']" }
    try {
      const el = document.querySelector(payload.selector);
      if (el) {
        el.click();
      }
    } catch (e) {
      console.error("CLICK_SELECTOR error", e);
    }
  }

  // UPLOAD_FILE и более сложные сценарии можно отдельно продумать:
  // там уже ограничения браузера по доступу к файлам.
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "REMOTE_COMMAND" && msg.command) {
    executeCommand(msg.command).then(() => {
      sendResponse({ status: "done" });
    });
    // вернуть true, чтобы указать, что ответ асинхронный
    return true;
  }
});
