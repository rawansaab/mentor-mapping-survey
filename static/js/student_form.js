const APP_CFG = window.APP_CFG || {};

const steps = Array.from(document.querySelectorAll(".step"));
const stepper = Array.from(document.querySelectorAll("#stepper li"));
const form = document.getElementById("wizardForm");
const nextBtn = document.getElementById("nextBtn");
const prevBtn = document.getElementById("prevBtn");
const submitBtn = document.getElementById("submitBtn");

let current = 0;
const multiSelectInstances = {};
let rankBaseOptions = [];


function setHidden(el, hidden) {
  if (!el) return;
  el.hidden = hidden;
}


function isHidden(el) {
  return Boolean(el.closest("[hidden]"));
}


function showStep(index) {
  steps.forEach((step, i) => step.classList.toggle("active", i === index));

  stepper.forEach((li, i) => {
    li.classList.toggle("active", i === index);
    li.classList.toggle("done", i < index);
  });

  prevBtn.disabled = index === 0;
  nextBtn.hidden = index === steps.length - 1;
  submitBtn.hidden = index !== steps.length - 1;

  if (index === steps.length - 1) {
    buildSummaryAndValidate();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}


window.goToStep = function goToStep(index) {
  current = index;
  showStep(current);
};


function validateStep(index) {
  const container = steps[index];
  const inputs = container.querySelectorAll("input[required], select[required], textarea[required]");

  for (const el of inputs) {
    if (isHidden(el)) continue;

    if (el.type === "radio") {
      const checked = container.querySelector(`input[name="${CSS.escape(el.name)}"]:checked`);
      if (!checked) return false;
      continue;
    }

    if (el.type === "checkbox") {
      if (!el.checked) return false;
      continue;
    }

    if (!String(el.value || "").trim()) return false;
  }

  return true;
}


nextBtn.addEventListener("click", () => {
  if (!validateStep(current)) {
    alert("נא למלא את כל שדות החובה בשלב זה כדי להתקדם.");
    return;
  }

  if (current < steps.length - 1) {
    current++;
    showStep(current);
  }
});


prevBtn.addEventListener("click", () => {
  if (current > 0) {
    current--;
    showStep(current);
  }
});


function getFieldByName(name) {
  return (APP_CFG.fields || []).find(f => f.name === name);
}


function getFieldIdByName(name) {
  const field = getFieldByName(name);
  return field ? field.id : null;
}


function getSelectedDomainNames() {
  const hidden = document.getElementById("domainsJoined");
  return String(hidden.value || "").split("; ").filter(Boolean);
}


function getRuleForYear(yearValue) {
  if (!yearValue || !APP_CFG.yearRules) return null;
  return APP_CFG.yearRules[yearValue] || null;
}


function looksLikeWelfare(value) {
  return String(value || "").includes("רווחה") || String(value || "").includes("שירותים חברתיים") || String(value || "").includes("לשכה");
}


function getAllowedFieldIdsForYear(yearValue) {
  const rule = getRuleForYear(yearValue);

  if (rule && Array.isArray(rule.fields) && rule.fields.length > 0) {
    return rule.fields;
  }

  // גיבוי לפי דרישת המרצים: אם לא הוגדר כלל בפאנל, שנה ב' תקבל רווחה בלבד
  if (String(yearValue || "").includes("שנה ב")) {
    const welfare = (APP_CFG.fields || []).filter(f => looksLikeWelfare(f.name) || looksLikeWelfare(f.id));
    return welfare.map(f => f.id);
  }

  return [];
}


function getAllowedPlacesForYear(yearValue, allowedFieldIds) {
  const rule = getRuleForYear(yearValue);

  if (rule && Array.isArray(rule.places) && rule.places.length > 0) {
    return rule.places;
  }

  if (allowedFieldIds.length > 0) {
    return (APP_CFG.trainingPlaces || [])
      .filter(place => Array.isArray(place.fieldIds) && place.fieldIds.some(fid => allowedFieldIds.includes(fid)))
      .map(place => place.name);
  }

  // גיבוי לפי דרישת המרצים: אם שנה ב' ללא כלל, מוצגים רק מקומות רווחה
  if (String(yearValue || "").includes("שנה ב")) {
    return (APP_CFG.trainingPlaces || [])
      .filter(place => looksLikeWelfare(place.name))
      .map(place => place.name);
  }

  return (APP_CFG.trainingPlaces || []).map(place => place.name);
}


function updateRankOptionsBase(newBase) {
  rankBaseOptions = [...newBase];
  document.querySelectorAll("select.rank").forEach(select => {
    select.value = "";
  });
  syncRanks();
}


function syncRanks() {
  const selects = Array.from(document.querySelectorAll("select.rank"));
  const chosen = selects.map(s => s.value).filter(Boolean);

  selects.forEach(select => {
    const currentValue = select.value;
    select.innerHTML = `<option value="">בחר/י</option>` + rankBaseOptions.map(value => {
      const disabled = chosen.includes(value) && value !== currentValue;
      const safeValue = escapeHtml(value);
      return `<option value="${safeValue}" ${disabled ? "disabled" : ""} ${currentValue === value ? "selected" : ""}>${safeValue}</option>`;
    }).join("");
  });
}


function applyYearRules() {
  const yearValue = document.getElementById("study_year").value;
  const allowedFieldIds = getAllowedFieldIdsForYear(yearValue);
  const allowedPlaces = getAllowedPlacesForYear(yearValue, allowedFieldIds);

  const domainsSelect = document.getElementById("domains");

  Array.from(domainsSelect.options).forEach(option => {
    const fieldId = option.dataset.fieldId;

    if (fieldId === "other") {
      option.hidden = allowedFieldIds.length > 0;
      option.selected = false;
      return;
    }

    const shouldShow = allowedFieldIds.length === 0 || allowedFieldIds.includes(fieldId);
    option.hidden = !shouldShow;

    if (!shouldShow) {
      option.selected = false;
    }
  });

  if (multiSelectInstances.domains) {
    multiSelectInstances.domains.refresh();
  }

  updateRankOptionsBase(allowedPlaces);

  const yearBNote = document.getElementById("year_b_note");
  setHidden(yearBNote, !String(yearValue || "").includes("שנה ב"));
}


function initCustomMultiSelect(config) {
  const select = document.getElementById(config.selectId);
  if (!select) return;

  const hiddenJoined = document.getElementById(config.hiddenId);
  const otherWrap = config.otherWrapId ? document.getElementById(config.otherWrapId) : null;
  const topDomainSelect = config.topDomainId ? document.getElementById(config.topDomainId) : null;
  const detailsWrap = config.detailsWrapId ? document.getElementById(config.detailsWrapId) : null;

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
      .filter(option => option.selected && !option.hidden)
      .map(option => option.value);
  }

  function updateUI() {
    let values = getValues();

    if (config.hasNoneOption && values.includes("אין") && values.length > 1) {
      Array.from(select.options).forEach(option => {
        option.selected = option.value === "אין";
      });
      values = ["אין"];
    }

    hiddenJoined.value = values.join("; ");

    if (otherWrap) {
      setHidden(otherWrap, !values.includes("אחר"));
    }

    if (detailsWrap) {
      const hideDetails = !values.length || (values.length === 1 && values[0] === "אין");
      setHidden(detailsWrap, hideDetails);
    }

    if (topDomainSelect) {
      topDomainSelect.innerHTML = `<option value="">בחר/י</option>` + values
        .filter(value => value !== "אחר")
        .map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
        .join("");
    }

    chips.innerHTML = "";

    if (!values.length) {
      chips.innerHTML = `<span class="placeholder">${escapeHtml(config.placeholder)}</span>`;
    } else {
      values.forEach(value => {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.innerHTML = `<span>${escapeHtml(value)}</span><button type="button" aria-label="הסרה">×</button>`;
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
      if (option.hidden) return;

      const item = document.createElement("div");
      item.className = "item";
      item.innerHTML = `<span>${escapeHtml(option.textContent)}</span><span class="check">${selectedSet.has(option.value) ? "✓" : ""}</span>`;

      item.addEventListener("click", () => {
        if (!option.selected && config.max && getValues().length >= config.max) {
          alert(`ניתן לבחור עד ${config.max} פריטים בלבד.`);
          return;
        }

        if (option.value === "אין" && config.hasNoneOption) {
          Array.from(select.options).forEach(o => {
            o.selected = o.value === "אין";
          });
        } else {
          option.selected = !option.selected;

          if (config.hasNoneOption) {
            const noneOption = Array.from(select.options).find(o => o.value === "אין");
            if (noneOption && option.value !== "אין") {
              noneOption.selected = false;
            }
          }
        }

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

  multiSelectInstances[config.selectId] = { refresh: updateUI };
  return multiSelectInstances[config.selectId];
}


function buildSummaryAndValidate() {
  const box = document.getElementById("summary");
  const confirms = document.getElementById("final_confirms");
  const fd = new FormData(form);

  const domains = String(fd.get("תחומים שנבחרו") || "").split("; ").filter(Boolean);
  const ranks = [
    fd.get("מקום הכשרה 1"),
    fd.get("מקום הכשרה 2"),
    fd.get("מקום הכשרה 3")
  ].filter(Boolean);

  const yearValue = fd.get("שנת לימודים") || "";
  const allowedFieldIds = getAllowedFieldIdsForYear(yearValue);
  const allowedPlaces = getAllowedPlacesForYear(yearValue, allowedFieldIds);

  const errors = [];

  if (allowedFieldIds.length > 0) {
    domains.forEach(domainName => {
      const fieldId = getFieldIdByName(domainName);
      if (fieldId && !allowedFieldIds.includes(fieldId)) {
        errors.push({
          title: `התחום "${domainName}" אינו מתאים לשנת הלימודים שנבחרה.`,
          desc: "יש לחזור לסעיף 2 ולבחור תחום מתוך האפשרויות שהוגדרו בפאנל המרצים.",
          step: 1
        });
      }
    });
  }

  ranks.forEach(place => {
    if (allowedPlaces.length > 0 && !allowedPlaces.includes(place)) {
      errors.push({
        title: `מקום ההכשרה "${place}" אינו מתאים לשנת הלימודים שנבחרה.`,
        desc: "יש לחזור לסעיף 2 ולבחור מקום הכשרה מתוך הרשימה המותרת.",
        step: 1
      });
    }
  });

  if (errors.length > 0) {
    confirms.hidden = true;
    submitBtn.hidden = true;

    box.innerHTML = `
      <div class="error-box">
        <h3>נמצאו חוסר התאמות בטופס</h3>
        ${errors.map(error => `
          <div class="error-item">
            <span class="error-title">${escapeHtml(error.title)}</span>
            <span class="error-desc">${escapeHtml(error.desc)}</span>
            <button type="button" class="btn-fix" onclick="goToStep(${error.step})">חזרה לתיקון</button>
          </div>
        `).join("")}
      </div>
    `;
    return;
  }

  confirms.hidden = false;
  submitBtn.hidden = false;

  const fullName = `${fd.get("שם פרטי") || ""} ${fd.get("שם משפחה") || ""}`.trim();

  box.innerHTML = `
    <div class="success-summary">
      <h3>בדיקת פרטים לפני שליחה</h3>
      <p><strong>שם:</strong> ${escapeHtml(fullName)}</p>
      <p><strong>שנת לימודים:</strong> ${escapeHtml(yearValue)}</p>
      <p><strong>תחומים:</strong> ${escapeHtml(domains.join(" / "))}</p>
      <p><strong>מקומות הכשרה:</strong> ${escapeHtml(ranks.join(" / "))}</p>
      <p>הכול נראה תקין. סמנ/י את ההצהרות ולחצ/י על שליחה.</p>
    </div>
  `;
}


function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


document.getElementById("mother_t").addEventListener("change", event => {
  setHidden(document.getElementById("other_mt_wrap"), event.target.value !== "אחר");
});


document.getElementById("study_year").addEventListener("change", event => {
  setHidden(document.getElementById("study_other_wrap"), event.target.value !== "אחר");
  applyYearRules();
});


document.getElementById("prev_training").addEventListener("change", event => {
  setHidden(document.querySelector(".prev-extra"), !event.target.value || event.target.value === "לא");
});


initCustomMultiSelect({
  selectId: "extra_langs",
  hiddenId: "extraLangsJoined",
  otherWrapId: "extra_other_wrap",
  placeholder: "בחר/י שפות נוספות"
});


initCustomMultiSelect({
  selectId: "domains",
  hiddenId: "domainsJoined",
  otherWrapId: "domains_other_wrap",
  topDomainId: "top_domain",
  placeholder: "בחר/י עד 3 תחומים",
  max: 3
});


initCustomMultiSelect({
  selectId: "adjustments",
  hiddenId: "adjJoined",
  otherWrapId: "adj_other_wrap",
  detailsWrapId: "adj_details_wrap",
  placeholder: "בחר/י סוגי התאמות",
  hasNoneOption: true
});


document.querySelectorAll("select.rank").forEach(select => {
  select.addEventListener("change", syncRanks);
});


document.querySelectorAll(".multi-check").forEach(label => {
  const input = label.querySelector("input");
  const sync = () => label.classList.toggle("active", input.checked);
  input.addEventListener("change", sync);
  sync();
});


rankBaseOptions = (APP_CFG.trainingPlaces || []).map(place => place.name);
applyYearRules();
showStep(current);
