function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


document.querySelectorAll(".tab-btn").forEach(button => {
  button.addEventListener("click", () => {
    const tabId = button.dataset.tab;

    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));

    button.classList.add("active");
    document.getElementById(tabId).classList.add("active");
  });
});


function removeAdminItem(button) {
  button.closest(".edit-item").remove();
}


function addDegreeTrack() {
  document.getElementById("degreeTracksList").insertAdjacentHTML("beforeend", `
    <div class="edit-item">
      <input type="text" class="track-name" value="" placeholder="שם מסלול">
      <button type="button" class="btn-del" onclick="removeAdminItem(this)">מחק</button>
    </div>
  `);
}


function addField() {
  document.getElementById("fieldsList").insertAdjacentHTML("beforeend", `
    <div class="edit-item double">
      <input type="text" class="field-id" value="" placeholder="מזהה באנגלית">
      <input type="text" class="field-name" value="" placeholder="שם התחום בעברית">
      <button type="button" class="btn-del" onclick="removeAdminItem(this)">מחק</button>
    </div>
  `);
}


function addPlace() {
  document.getElementById("placesList").insertAdjacentHTML("beforeend", `
    <div class="edit-item triple">
      <input type="text" class="place-name" value="" placeholder="שם מקום הכשרה">
      <input type="text" class="place-fields" value="" placeholder="מזהי תחומים מופרדים בפסיק">
      <button type="button" class="btn-del" onclick="removeAdminItem(this)">מחק</button>
    </div>
  `);
}


function addYearRule() {
  document.getElementById("yearRulesList").insertAdjacentHTML("beforeend", `
    <div class="edit-item triple year-rule-item">
      <input type="text" class="rule-year" value="" placeholder="לדוגמה: תואר ראשון - שנה ב'">
      <input type="text" class="rule-fields" value="" placeholder="מזהי תחומים מותרים">
      <input type="text" class="rule-places" value="" placeholder="מקומות מותרים, הפרדה עם |">
      <button type="button" class="btn-del" onclick="removeAdminItem(this)">מחק</button>
    </div>
  `);
}


function addAccommodation() {
  document.getElementById("accommodationsList").insertAdjacentHTML("beforeend", `
    <div class="edit-item">
      <input type="text" class="acc-name" value="" placeholder="סוג התאמה">
      <button type="button" class="btn-del" onclick="removeAdminItem(this)">מחק</button>
    </div>
  `);
}


function addMentorStatus() {
  document.getElementById("mentorStatusesList").insertAdjacentHTML("beforeend", `
    <div class="edit-item">
      <input type="text" class="mentor-status" value="" placeholder="סטטוס מדריך">
      <button type="button" class="btn-del" onclick="removeAdminItem(this)">מחק</button>
    </div>
  `);
}


function addFeedbackPoint() {
  document.getElementById("feedbackPointsList").insertAdjacentHTML("beforeend", `
    <div class="edit-item">
      <input type="text" class="feedback-point" value="" placeholder="נקודה לחוות דעת">
      <button type="button" class="btn-del" onclick="removeAdminItem(this)">מחק</button>
    </div>
  `);
}


function splitComma(value) {
  return String(value || "")
    .split(",")
    .map(v => v.trim())
    .filter(Boolean);
}


function splitPipe(value) {
  return String(value || "")
    .split("|")
    .map(v => v.trim())
    .filter(Boolean);
}


function normalizeTrackName(value) {
  return String(value || "").trim().replaceAll("הסבה", "השלמות");
}


function prepareAdminData() {
  const degreeTracks = Array.from(document.querySelectorAll("#degreeTracksList .track-name"))
    .map(input => normalizeTrackName(input.value))
    .filter(Boolean)
    .map(name => ({ name }));

  const fields = Array.from(document.querySelectorAll("#fieldsList .edit-item"))
    .map(item => {
      const id = item.querySelector(".field-id").value.trim();
      const name = item.querySelector(".field-name").value.trim().replaceAll("הסבה", "השלמות");
      return { id, name, allowedDegreeYears: [] };
    })
    .filter(field => field.id && field.name);

  const trainingPlaces = Array.from(document.querySelectorAll("#placesList .edit-item"))
    .map(item => {
      const name = item.querySelector(".place-name").value.trim();
      const fieldIds = splitComma(item.querySelector(".place-fields").value);
      return { name, fieldIds };
    })
    .filter(place => place.name);

  const yearRules = {};
  Array.from(document.querySelectorAll("#yearRulesList .edit-item")).forEach(item => {
    const year = item.querySelector(".rule-year").value.trim();
    const fields = splitComma(item.querySelector(".rule-fields").value);
    const places = splitPipe(item.querySelector(".rule-places").value);

    if (year) {
      yearRules[year] = { fields, places };
    }
  });

  const accommodationTypes = Array.from(document.querySelectorAll("#accommodationsList .acc-name"))
    .map(input => input.value.trim())
    .filter(Boolean);

  const mentorStatuses = Array.from(document.querySelectorAll("#mentorStatusesList .mentor-status"))
    .map(input => input.value.trim())
    .filter(Boolean);

  const feedbackPoints = Array.from(document.querySelectorAll("#feedbackPointsList .feedback-point"))
    .map(input => input.value.trim())
    .filter(Boolean);

  document.getElementById("degreeTracks_json").value = JSON.stringify(degreeTracks);
  document.getElementById("fields_json").value = JSON.stringify(fields);
  document.getElementById("trainingPlaces_json").value = JSON.stringify(trainingPlaces);
  document.getElementById("yearRules_json").value = JSON.stringify(yearRules);
  document.getElementById("accommodationTypes_json").value = JSON.stringify(accommodationTypes);
  document.getElementById("mentorStatuses_json").value = JSON.stringify(mentorStatuses);
  document.getElementById("feedbackPoints_json").value = JSON.stringify(feedbackPoints);

  return true;
}
