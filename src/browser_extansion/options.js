// options.js
document.addEventListener("DOMContentLoaded", () => {
  const apiUrlInput = document.getElementById("apiUrl");
  const statusEl = document.getElementById("status");
  const saveBtn = document.getElementById("save");

  chrome.storage.sync.get(["apiUrl"], (data) => {
    if (data.apiUrl) apiUrlInput.value = data.apiUrl;
  });

  saveBtn.addEventListener("click", () => {
    const apiUrl = apiUrlInput.value.trim();

    chrome.storage.sync.set({ apiUrl }, () => {
      statusEl.textContent = "Сохранено";
      setTimeout(() => (statusEl.textContent = ""), 1500);
    });
  });
});
