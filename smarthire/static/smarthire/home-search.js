(() => {
  const form = document.querySelector(".home-job-search[data-suggestions-url]");
  if (!form) return;

  let timer;
  let controller;
  form.querySelectorAll("[data-search-kind]").forEach((input) => {
    const list = document.getElementById(input.getAttribute("list"));
    if (!list) return;

    const loadSuggestions = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(async () => {
        controller?.abort();
        controller = new AbortController();
        const params = new URLSearchParams({ kind: input.dataset.searchKind, q: input.value.trim() });
        try {
          const response = await fetch(`${form.dataset.suggestionsUrl}?${params}`, { signal: controller.signal });
          if (!response.ok) return;
          const data = await response.json();
          list.replaceChildren(...data.suggestions.map((value) => {
            const option = document.createElement("option");
            option.value = value;
            return option;
          }));
        } catch (error) {
          if (error.name !== "AbortError") console.warn("Job search suggestions are unavailable.");
        }
      }, 120);
    };

    input.addEventListener("focus", loadSuggestions);
    input.addEventListener("input", loadSuggestions);
  });
})();
