(() => {
  const root = document.querySelector(".guidance-chat");
  if (!root) return;

  const launcher = root.querySelector(".chat-launcher");
  const panel = root.querySelector(".chat-panel");
  const closeButton = root.querySelector(".chat-close");
  const form = root.querySelector(".chat-form");
  const input = root.querySelector("#guidance-chat-input");
  const log = root.querySelector(".chat-messages");
  const sendButton = form.querySelector("button[type=submit]");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;

  const openChat = (open) => {
    panel.hidden = !open;
    launcher.setAttribute("aria-expanded", String(open));
    if (open) input.focus();
    else launcher.focus();
  };
  launcher.addEventListener("click", () => openChat(panel.hidden));
  closeButton.addEventListener("click", () => openChat(false));

  const scrollToLatest = () => { log.scrollTop = log.scrollHeight; };
  const addBubble = (text, kind = "assistant") => {
    const bubble = document.createElement("p");
    bubble.className = `chat-bubble chat-${kind}`;
    bubble.textContent = text;
    log.append(bubble);
    scrollToLatest();
    return bubble;
  };
  const addLinks = (items, className = "chat-actions") => {
    if (!items?.length) return;
    const group = document.createElement("div");
    group.className = className;
    items.forEach((item) => {
      const link = document.createElement("a");
      const target = new URL(item.url, window.location.origin);
      if (target.origin !== window.location.origin) return;
      link.href = target.href;
      link.textContent = item.label;
      group.append(link);
    });
    if (group.childElementCount) log.append(group);
    scrollToLatest();
  };

  const sendMessage = async (message) => {
    const text = message.trim();
    if (!text || sendButton.disabled) return;
    addBubble(text, "user");
    input.value = "";
    sendButton.disabled = true;
    const loading = addBubble("Thinking…", "loading");
    try {
      const response = await fetch(root.dataset.endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ message: text }),
      });
      const data = await response.json();
      loading.remove();
      if (!response.ok) throw new Error(data.error || "I couldn’t send that. Please try again.");
      addBubble(data.reply);
      addLinks(data.jobs?.map((job) => ({
        label: `${job.title} · ${job.match}% match`,
        url: job.url,
      })), "chat-job-list");
      addLinks(data.actions);
    } catch (error) {
      loading.remove();
      addBubble(error.message || "I’m having trouble connecting. Please try again or contact SmartHire.");
    } finally {
      sendButton.disabled = false;
      input.focus();
    }
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
  });
  root.querySelectorAll("[data-chat-prompt]").forEach((button) => {
    button.addEventListener("click", () => sendMessage(button.dataset.chatPrompt));
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) openChat(false);
  });
})();
