function setHidden(el, hidden) {
  if (!el) return;
  el.hidden = hidden;
}


function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function initCustomMultiSelect(config) {
  const select = document.getElementById(config.selectId);
  if (!select) return;

  const hiddenJoined = document.getElementById(config.hiddenId);
  hiddenJoined.required = true;
  select.removeAttribute("required");

  const wrap = document.createElement("div");
  wrap.className = "tag-ms";

  const control = document.createElement("div");
  control.className = "control";

  const chips = document.createElement("div");
  chips.className = "chips";

  const menu = document.createElement("div");
  menu.className = "menu";

  control.appendChild(chips);
  wrap.appendChild(control);
  wrap.appendChild(menu);
  select.after(wrap);
  select.hidden = true;

  function getValues() {
    return Array.from(select.options)
      .filter(option => option.selected)
      .map(option => option.value);
  }

  function updateUI() {
    const values = getValues();
    hiddenJoined.value = values.join("; ");

    chips.innerHTML = "";
    if (!values.length) {
      chips.innerHTML = `<span class="placeholder">${escapeHtml(config.placeholder)}</span>`;
    } else {
      values.forEach(value => {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.innerHTML = `<span>${escapeHtml(value)}</span><button type="button">×</button>`;
        chip.querySelector("button").addEventListener("click", event => {
          event.stopPropagation();
          const option = Array.from(select.options).find(o => o.value === value);
          if (option) option.selected = false;
          updateUI();
        });
        chips.appendChild(chip);
      });
    }

    menu.innerHTML = "";
    const selectedSet = new Set(values);

    Array.from(select.options).forEach(option => {
      const item = document.createElement("div");
      item.className = "item";
      item.innerHTML = `<span>${escapeHtml(option.textContent)}</span><span class="check">${selectedSet.has(option.value) ? "✓" : ""}</span>`;

      item.addEventListener("click", () => {
        option.selected = !option.selected;
        updateUI();
      });

      menu.appendChild(item);
    });
  }

  control.addEventListener("click", () => wrap.classList.toggle("open"));

  document.addEventListener("click", event => {
    if (!wrap.contains(event.target)) {
      wrap.classList.remove("open");
    }
  });

  updateUI();
}


initCustomMultiSelect({
  selectId: "mentor_fields",
  hiddenId: "mentorFieldsJoined",
  placeholder: "בחר/י תחומי התמחות"
});


initCustomMultiSelect({
  selectId: "mentor_years",
  hiddenId: "mentorYearsJoined",
  placeholder: "בחר/י שנות לימוד מתאימות"
});


document.getElementById("mentorMappingForm").addEventListener("submit", event => {
  const requiredInputs = event.currentTarget.querySelectorAll("input[required], select[required], textarea[required]");

  for (const el of requiredInputs) {
    if (!String(el.value || "").trim()) {
      event.preventDefault();
      alert("נא למלא את כל שדות החובה לפני שליחה.");
      return;
    }
  }
});
