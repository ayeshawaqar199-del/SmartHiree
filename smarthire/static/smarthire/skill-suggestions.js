(() => {
  const loader = document.currentScript;
  const endpoint = loader?.dataset.suggestionsUrl || "/skills/suggest/";
  const inputs = document.querySelectorAll(
    'input[name="skills"], input[name="required_skills"], input[name="preferred_skills"]'
  );

  inputs.forEach((input, index) => {
    const wrapper = input.parentElement;
    wrapper.classList.add("skill-autocomplete");

    const list = document.createElement("div");
    list.className = "skill-suggestion-list";
    list.id = `skill-suggestions-${index}`;
    list.setAttribute("role", "listbox");
    list.hidden = true;
    wrapper.append(list);

    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", list.id);
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("autocomplete", "off");

    let timer;
    let controller;
    let activeIndex = -1;
    let currentSuggestions = [];

    const hide = () => {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      activeIndex = -1;
    };

    const selectSkill = (skill) => {
      const parts = input.value.split(",");
      parts[parts.length - 1] = skill;
      const selected = parts.map((part) => part.trim()).filter(Boolean);
      const unique = selected.filter((part, position) =>
        selected.findIndex((item) => item.toLocaleLowerCase() === part.toLocaleLowerCase()) === position
      );
      input.value = `${unique.join(", ")}, `;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      hide();
    };

    const render = (suggestions) => {
      currentSuggestions = suggestions;
      activeIndex = -1;
      list.replaceChildren();
      if (!suggestions.length) {
        hide();
        return;
      }

      suggestions.forEach((skill, optionIndex) => {
        const option = document.createElement("button");
        option.type = "button";
        option.className = "skill-suggestion-option";
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", "false");
        option.textContent = skill;
        option.addEventListener("mousedown", (event) => event.preventDefault());
        option.addEventListener("click", () => selectSkill(skill));
        list.append(option);
      });
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
    };

    const update = async () => {
      const prefix = input.value.split(",").pop().trim();
      if (prefix.length < 2) {
        hide();
        return;
      }
      controller?.abort();
      controller = new AbortController();
      try {
        const response = await fetch(`${endpoint}?q=${encodeURIComponent(prefix)}`, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Skill suggestions are unavailable");
        const data = await response.json();
        render(data.suggestions || []);
      } catch (error) {
        if (error.name !== "AbortError") hide();
      }
    };

    input.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(update, 120);
    });

    input.addEventListener("keydown", (event) => {
      if (list.hidden || !currentSuggestions.length) return;
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const direction = event.key === "ArrowDown" ? 1 : -1;
        activeIndex = (activeIndex + direction + currentSuggestions.length) % currentSuggestions.length;
        [...list.children].forEach((option, optionIndex) => {
          const selected = optionIndex === activeIndex;
          option.setAttribute("aria-selected", String(selected));
          option.classList.toggle("is-active", selected);
        });
      } else if (event.key === "Enter" && activeIndex >= 0) {
        event.preventDefault();
        selectSkill(currentSuggestions[activeIndex]);
      } else if (event.key === "Escape") {
        hide();
      }
    });

    input.addEventListener("blur", () => window.setTimeout(hide, 140));
  });
})();
