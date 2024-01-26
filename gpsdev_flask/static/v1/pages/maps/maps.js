import { alertsToggle } from "../../../v1/alerts.js";
import { hideModal } from "../../../v1/modal.js";
import { dictionary } from "../../../v1/translation_dict.js";

// check if the browser language is different
let browserLanguage = navigator.language || navigator.userLanguage;
if (browserLanguage !== "ru-RU") {
  document.getElementById("startDateOfPeriod").style.width = "130px";
  document.getElementById("endDateOfPeriod").style.width = "130px";
}

// create divisions list from access. If have data in localStorage, set selected division from localStorage
let divisionField = document.getElementById("divisionSelect");
let access = JSON.parse(localStorage.getItem("access"));
access.forEach((d) => {
  const divisionName = d.division;
  let option = document.createElement("option");
  option.setAttribute("division_id", d.division_id);
  option.innerText = divisionName;
  if (
    d.division_id == localStorage.getItem("previous-selected-division-maps")
  ) {
    option.selected = true;
  }
  divisionField.append(option);
});

// represents name and index of each month
let monthDict = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];

let previousMonthDate = new Date().getMonth() - 1;
let currentMonthDate = new Date().getMonth();
if (previousMonthDate == -1) {
  previousMonthDate = 11;
  console.log(previousMonthDate);
}
let previousMonthName = monthDict[previousMonthDate];
let currentMonthName = monthDict[currentMonthDate];

let previousCurrentMonth = document.getElementById("previousCurrentMonth");
previousCurrentMonth.innerText = previousMonthName + "-" + currentMonthName;
previousCurrentMonth.onclick = previousMonthF;

let currentMonth = document.getElementById("currentMonth");
currentMonth.innerText = currentMonthName;
currentMonth.onclick = currentMonthF;

let startDate = document.getElementById("startDateOfPeriod");
let endDate = document.getElementById("endDateOfPeriod");

// if have data in localStorage, set dates values and ojects/bound from localStorage
localStorage.getItem("previous-selected-start-date") != null
  ? (startDate.value = localStorage.getItem(
      "previous-selected-start-date-maps"
    ))
  : null;
localStorage.getItem("previous-selected-end-date") != null
  ? (endDate.value = localStorage.getItem("previous-selected-end-date-maps"))
  : null;
let objectsOrBoundField = [
  ...document.getElementById("objectsOrBoundSelect").options,
];
objectsOrBoundField.forEach((c) => {
  if (
    c.getAttribute("counts") ==
    localStorage.getItem("previous-selected-objectsOrBound")
  ) {
    c.selected = true;
  }
});

function previousMonthF(e) {
  e.preventDefault();

  startDate.classList.remove("date-highlight", "fade-out-box");
  endDate.classList.remove("date-highlight", "fade-out-box");

  startDate.value = "";
  endDate.value = "";

  let date = new Date();
  let month = date.getMonth();
  let year = date.getFullYear();
  let firstDate = new Date(year, month - 1, 1, 12).toISOString().split("T")[0];
  let lastDate = new Date(year, month + 1, 0, 12).toISOString().split("T")[0];

  startDate.value = firstDate;
  endDate.value = lastDate;

  startDate.classList.add("date-highlight");
  endDate.classList.add("date-highlight");
  setTimeout(() => {
    startDate.classList.add("fade-out-box");
    endDate.classList.add("fade-out-box");
    setTimeout(() => {
      startDate.classList.remove("date-highlight", "fade-out-box");
      endDate.classList.remove("date-highlight", "fade-out-box");
    }, 600);
  }, 600);
}

//set dates values with start and end date of current month
function currentMonthF(e) {
  e.preventDefault();

  startDate.classList.remove("date-highlight", "fade-out-box");
  endDate.classList.remove("date-highlight", "fade-out-box");

  startDate.value = "";
  endDate.value = "";

  let date = new Date();
  let month = date.getMonth();
  let year = date.getFullYear();
  let firstDate = new Date(year, month, 1, 12).toISOString().split("T")[0];
  let lastDate = new Date(year, month + 1, 0, 12).toISOString().split("T")[0];

  startDate.value = firstDate;
  endDate.value = lastDate;

  startDate.classList.add("date-highlight");
  endDate.classList.add("date-highlight");

  setTimeout(() => {
    startDate.classList.add("fade-out-box");
    endDate.classList.add("fade-out-box");
    setTimeout(() => {
      startDate.classList.remove("date-highlight", "fade-out-box");
      endDate.classList.remove("date-highlight", "fade-out-box");
    }, 600);
  }, 600);
}

let requestMapBtn = document.getElementById("requestBtn");
requestMapBtn.onclick = requestMap;

//if localStorage have all the data is necessary for the request, make a request automatically
if (
  localStorage.getItem("previous-selected-division-maps") &&
  localStorage.getItem("previous-selected-start-date-maps") &&
  localStorage.getItem("previous-selected-end-date-maps") &&
  localStorage.getItem("previous-selected-objectsOrBound")
) {
  requestMapBtn.click();
}

//collect all data from request fields
function getMapParameters(e) {
  e.preventDefault();
  let options = document.getElementById("divisionSelect");
  let divisionId = Number(
    options.options[options.selectedIndex].getAttribute("division_id")
  );
  let startDate = document.getElementById("startDateOfPeriod").value;
  let endDate = document.getElementById("endDateOfPeriod").value;
  let objectsOrBound = document.getElementById("objectsOrBoundSelect");
  let countsR =
    objectsOrBound.options[objectsOrBound.selectedIndex].getAttribute("counts");

  $("#preLoadContainer")[0].style.display = "flex";

  if (startDate == "" || endDate == "") {
    $("#preLoadContainer")[0].style.display = "none";
    document.getElementById("requestBtn").disabled = false;
    alertsToggle("Укажите дату!", "warning", 5000);
    return;
  }
  let parameters = {
    division: divisionId,
    date_from: startDate,
    date_to: endDate,
    counts: countsR,
  };

  localStorage.setItem("previous-selected-start-date-maps", startDate);
  localStorage.setItem("previous-selected-end-date-maps", endDate);
  localStorage.setItem("previous-selected-division-maps", divisionId);
  localStorage.setItem("previous-selected-objectsOrBound", countsR);

  console.log(parameters);
  return parameters;
}

//call the function which collect data and then call the function with fetch
function requestMap(e) {
  document.getElementById("requestBtn").disabled = true;
  let parameters = getMapParameters(e);
  if (parameters == undefined) return;
  getMap(parameters);
}

function getMap(parameters) {
  let map = document.getElementById("mapContainer");
  map.style.display = "none";
  map ? (map.innerHTML = "") : null;

  let url;
  parameters.counts == "false"
    ? (url = "/api/map/objects")
    : (url = "/api/map/bindings");

  console.log(url);
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }
      return Promise.reject(response);
    })
    .then((data) => {
      console.log(data);
      $("#preLoadContainer")[0].style.display = "none";
      map.style.display = "flex";
      document.getElementById("requestBtn").disabled = false;
      let mapContainer = document.getElementById("mapContainer");
      mapContainer.innerHTML = data.map;
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((entry) => {
            let splitEntry = entry.split(":");
            let nameField = splitEntry[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newEntry = newNameField + ": " + splitEntry[1];
            alertsToggle(newEntry, "danger", 3000);
          });
        });
      }
      if (response.status >= 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
}
