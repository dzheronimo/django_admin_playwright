// background.js

// Значение по умолчанию для локальной разработки
const DEFAULT_API_BASE = "http://127.0.0.1:8000/api/agent/";

// Берём apiUrl из настроек (если есть), иначе используем дефолт
async function getApiBase() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["apiUrl"], (data) => {
      let base = data.apiUrl || DEFAULT_API_BASE;

      // Нормализуем: всегда с завершающим /
      if (!base.endsWith("/")) {
        base = base + "/";
      }
      resolve(base);
    });
  });
}

// Получаем токен по текущей сессии пользователя (кука Django)
async function fetchToken(apiBase) {
  try {
    const resp = await fetch(apiBase + "token/", {
      method: "GET",
      credentials: "include", // подставляем куки сессии
    });

    if (resp.status === 401) {
      console.log("[Agent] Пользователь не авторизован на сайте");
      return null;
    }

    if (!resp.ok) {
      console.warn("[Agent] Ошибка получения токена:", resp.status);
      return null;
    }

    const data = await resp.json();
    if (!data.token) {
      console.warn("[Agent] В ответе нет токена");
      return null;
    }

    return data.token;
  } catch (err) {
    console.error("[Agent] Ошибка запроса токена:", err);
    return null;
  }
}

async function pollServer() {
  const apiBase = await getApiBase();
  const token = await fetchToken(apiBase);
  if (!token) {
    // Не залогинен или не получили токен — тихо выходим
    return;
  }

  try {
    // ping (опционально)
    await fetch(apiBase + "ping/", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, status: "idle" }),
    });

    // next command
    const resp = await fetch(
      apiBase + "next-command/?token=" + encodeURIComponent(token),
      {
        method: "GET",
        credentials: "include",
      }
    );

    if (!resp.ok) {
      console.warn("[Agent] next-command error", resp.status);
      return;
    }

    const data = await resp.json();
    if (!data.command) {
      // команд нет
      return;
    }

    const command = data.command;
    console.log("[Agent] Получена команда:", command);

    // отправляем в активную вкладку (упрощённо — одну)
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      console.warn("[Agent] Нет активной вкладки для выполнения команды");
      return;
    }

    // Оборачиваем sendMessage в Promise, чтобы дождаться ответа
    const response = await new Promise((resolve) => {
      chrome.tabs.sendMessage(
        tab.id,
        { type: "REMOTE_COMMAND", command },
        (respFromContent) => {
          if (chrome.runtime.lastError) {
            console.warn(
              "[Agent] Ошибка отправки в content script:",
              chrome.runtime.lastError
            );
            resolve({ status: "error", message: chrome.runtime.lastError.message });
          } else {
            resolve(respFromContent || { status: "done" });
          }
        }
      );
    });

    // Репортим результат выполнения команды на сервер (MVP-реализация)
    const resultStatus =
      response && response.status === "error" ? "error" : "done";
    const resultText = (response && response.message) || "";

    await fetch(apiBase + "command-result/", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        token,
        command_id: command.id,
        status: resultStatus,
        result_text: resultText,
      }),
    });
  } catch (err) {
    console.error("[Agent] pollServer error:", err);
  }
}

// таймер опроса
setInterval(() => {
  // промис просто игнорируем, нам не нужно ждать
  pollServer();
}, 5000); // каждые 5 сек
