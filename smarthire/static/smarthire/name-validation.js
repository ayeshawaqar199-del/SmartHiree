(() => {
  const letter = /\p{L}/u;
  const usernameCharacter = /[\p{L}\p{N}_.@+-]/u;

  document.querySelectorAll("[data-alpha-only]").forEach((field) => {
    const mode = field.dataset.alphaOnly;
    const clean = (value) => {
      let result = "";
      for (const character of value) {
        if (mode === "username") {
          if (usernameCharacter.test(character)) result += character;
        } else if (letter.test(character)) {
          result += character;
        } else if (mode === "words" && /\s/u.test(character) && result && !result.endsWith(" ")) {
          result += " ";
        }
      }
      return mode === "words" ? result.replace(/\s+$/u, "") : result;
    };

    field.addEventListener("input", () => {
      const start = field.selectionStart;
      const before = field.value;
      const after = clean(before);
      if (before !== after) {
        const removedBeforeCaret = clean(before.slice(0, start)).length;
        field.value = after;
        field.setSelectionRange(removedBeforeCaret, removedBeforeCaret);
      }
    });

    field.addEventListener("paste", (event) => {
      const pasted = event.clipboardData?.getData("text") || "";
      if (!pasted) return;
      event.preventDefault();
      const start = field.selectionStart;
      const end = field.selectionEnd;
      const inserted = clean(pasted);
      field.setRangeText(inserted, start, end, "end");
      field.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });
})();