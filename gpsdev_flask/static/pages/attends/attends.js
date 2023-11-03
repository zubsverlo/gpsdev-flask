import { alertsToggle } from "../../alerts.js";
import { hideModal } from "../../modal.js";
import { dictionary } from "../../translation_dict.js";

let attendsTable;
let currentRowOfTable;

// check if the browser language is different
let browserLanguage = navigator.language || navigator.userLanguage;
if (browserLanguage !== "ru-RU") {
  document.getElementById("startDateOfPeriod").style.width = "130px";
  document.getElementById("endDateOfPeriod").style.width = "130px";
}

const closeModal = document.getElementById("closeModal");
closeModal.addEventListener("click", hideModal);

// create divisions list from access. If have data in localStorage, set selected division from localStorage
let divisionField = document.getElementById("divisionSelect");
let access = JSON.parse(localStorage.getItem("access"));
access.forEach((d) => {
  const divisionName = d.division;
  let option = document.createElement("option");
  option.setAttribute("division_id", d.division_id);
  option.innerText = divisionName;
  if (d.division_id == localStorage.getItem("previous-selected-division")) {
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

// if have data in localStorage, set dates values and time/quantity from localStorage
localStorage.getItem("previous-selected-start-date") != null
  ? (startDate.value = localStorage.getItem("previous-selected-start-date"))
  : null;
localStorage.getItem("previous-selected-end-date") != null
  ? (endDate.value = localStorage.getItem("previous-selected-end-date"))
  : null;
let timeOrQuantityField = [
  ...document.getElementById("timeOrQuantitySelect").options,
];
timeOrQuantityField.forEach((c) => {
  if (
    c.getAttribute("counts") ==
    localStorage.getItem("previous-selected-timeOrQuantity")
  ) {
    c.selected = true;
  }
});

// set dates values with start date of previous month and end date of current month
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

let requestTableBtn = document.getElementById("requestBtn");
requestTableBtn.onclick = requestTable;

//if localStorage have all the data is necessary for the request, make a request automatically
if (
  localStorage.getItem("previous-selected-division") &&
  localStorage.getItem("previous-selected-start-date") &&
  localStorage.getItem("previous-selected-end-date") &&
  localStorage.getItem("previous-selected-timeOrQuantity")
) {
  requestTableBtn.click();
}

//collect all data from request fields
function getTableParameters(e) {
  e.preventDefault();
  let options = document.getElementById("divisionSelect");
  let divisionId = Number(
    options.options[options.selectedIndex].getAttribute("division_id")
  );
  let startDate = document.getElementById("startDateOfPeriod").value;
  let endDate = document.getElementById("endDateOfPeriod").value;
  let timeOrQuantity = document.getElementById("timeOrQuantitySelect");
  let countsR =
    timeOrQuantity.options[timeOrQuantity.selectedIndex].getAttribute("counts");

  let date = new Date();
  let month = date.getMonth();

  if (localStorage.getItem("lastAlertMonth") != month) {
    alertsToggle(
      `Если отображаются не все сотрудники, запросите отчет за "${previousMonthName}-${currentMonthName}"!`,
      "info",
      10000
    );
    localStorage.setItem("lastAlertMonth", month);
  }

  $("#preLoadContainer")[0].style.display = "flex";

  if (startDate == "" || endDate == "") {
    $("#preLoadContainer")[0].style.display = "none";
    alertsToggle("Укажите дату!", "warning", 5000);
    return;
  }
  let parameters = {
    division: divisionId,
    date_from: startDate,
    date_to: endDate,
    counts: countsR,
  };

  localStorage.setItem("previous-selected-start-date", startDate);
  localStorage.setItem("previous-selected-end-date", endDate);
  localStorage.setItem("previous-selected-division", divisionId);
  localStorage.setItem("previous-selected-timeOrQuantity", countsR);

  console.log(parameters);
  return parameters;
}

//call the function which collect data and then call the function with fetch
function requestTable(e) {
  document.getElementById("requestBtn").disabled = true;
  let parameters = getTableParameters(e);
  if (parameters == undefined) return;
  getTable(parameters);
}

//dictionary for jspreadsheet table columns
const formatDict = {
  name: {
    title: "Сотрудники",
    name: "name",
    wordWrap: true,
    width: 150,
    align: "left",
  },
  name_id: { title: "name_id", name: "name_id", type: "hidden" },
  object: { title: "Подопечные", name: "object", width: 280, align: "left" },
  object_id: { title: "object_id", name: "object_id", type: "hidden" },
  comment: {
    title: "Комментарии",
    name: "comment",
    width: 140,
    align: "left",
    wordWrap: false,
  },
  frequency: { title: "Кол-во", name: "frequency", width: 58 },
  income: { title: "Доход", name: "income", width: 70 },
};

let duplicateData = null;

//request table data from server and create table
function getTable(parameters) {
  let table = document.getElementById("attendsTable");
  table ? (table.innerHTML = "") : null;
  $.ajax({
    url: "/api/report",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(parameters),
  })
    .done(function (data) {
      console.log("data: ", data);
      duplicateData = data.duplicated_attends;
      let columns = data.horizontal_report.columns;
      let newColumns = [];

      columns.forEach((column) => {
        let newColumn = formatDict[column]
          ? formatDict[column]
          : { title: column, name: column, width: 70 };

        newColumns.push(newColumn);
      });
      $("#preLoadContainer")[0].style.display = "none";

      let windowHeight = window.innerHeight - 180;

      attendsTable = jspreadsheet(document.getElementById("attendsTable"), {
        columns: newColumns,
        data: data.horizontal_report.data,
        freezeColumns: 4,
        search: true,
        editable: false,
        freezeRows: 2,
        tableOverflow: true,
        tableHeight: windowHeight + "px",
        tableWidth: "100%",
        lazyLoading: false,
        text: {
          search: "Поиск",
        },
      });
      createToolbar();
      dateFormatColoredWeekends();
      reMergeCells();

      document.getElementById("requestBtn").disabled = false;

      if (localStorage.getItem("toggleComments") === "hide") {
        attendsTable.hideColumn(2);
        attendsTable.options.columns[2].type = "hidden";
      }
      document
        .getElementById("attendsTable")
        .addEventListener("keydown", tableKeyEvents);
    })
    .fail(function (xhr, status, error) {
      let json = xhr.responseJSON;
      if (xhr.status == 500) {
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
      if (xhr.status == 422) {
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(json.detail, "danger", 6000);
      }
    });
}

//set eventListener on the window, when window resize - resize the table
window.addEventListener("resize", () => {
  let windowHeight = window.innerHeight - 180;
  document.getElementById("attendsTable")
    ? (document.getElementById("attendsTable").children[2].style.maxHeight =
        windowHeight + "px")
    : null;
});

//set orange color on weekend dates
function dateFormatColoredWeekends() {
  let header = document
    .getElementById("attendsTable")
    .getElementsByTagName("thead")[0]
    .getElementsByTagName("tr")[0].children;
  for (let i = 0; i < header.length; i++) {
    let date = new Date(header[i].innerText);
    let day = date.getDay();

    if (isNaN(day)) continue;

    let formatedDate = date.toLocaleDateString("ru").slice(0, 5);
    if (day == 0 || day == 6) {
      header[i].innerText = formatedDate;
      header[i].style.backgroundColor = "#f6b26b";
    } else header[i].innerText = formatedDate;
  }
}

//create an active toolbar
function createToolbar() {
  let customToolbar = document.createElement("div");
  customToolbar.id = "customToolbar";

  let addEmployeeBtn = document.createElement("button");
  addEmployeeBtn.id = "addEmployeeBtn";
  addEmployeeBtn.innerHTML = `<span class="material-icons">person_add</span>`;
  addEmployeeBtn.title = "Добавить сотрудника в отчет";
  addEmployeeBtn.onclick = addEmployeeInTable;

  let downloadXlsxBtn = document.createElement("button");
  downloadXlsxBtn.id = "downloadXlsxBtn";
  downloadXlsxBtn.innerHTML = `<span class="material-icons">download</span>`;
  downloadXlsxBtn.title = "Скачать таблицу Excel";
  downloadXlsxBtn.onclick = downloadXlsx;

  let toggleCommentsBtn = document.createElement("button");
  toggleCommentsBtn.id = "toggleCommentsBtn";
  toggleCommentsBtn.title = "Скрыть/Показать столбец с комментариями";
  toggleCommentsBtn.onclick = toggleComments;
  if (
    localStorage.getItem("toggleComments") == "show" ||
    localStorage.getItem("toggleComments") == null
  ) {
    toggleCommentsBtn.innerHTML = `<span class="material-icons">speaker_notes_off</span>`;
  } else if (localStorage.getItem("toggleComments") == "hide") {
    toggleCommentsBtn.innerHTML = `<span class="material-icons">speaker_notes</span>`;
  }

  let duplicatesBtn = document.createElement("button");
  duplicatesBtn.id = "duplicatesBtn";
  duplicatesBtn.innerHTML = `<span class="material-icons">people</span>`;
  duplicatesBtn.title = "Показать дубликаты";
  duplicatesBtn.onclick = showDuplicates;

  let refreshTableBtn = document.createElement("button");
  refreshTableBtn.id = "refreshTableBtn";
  refreshTableBtn.innerHTML = `<span class="material-icons">refresh</span>`;
  refreshTableBtn.title = "Обновить данные в отчете";
  refreshTableBtn.onclick = updateTable;

  customToolbar.append(
    addEmployeeBtn,
    downloadXlsxBtn,
    toggleCommentsBtn,
    duplicatesBtn,
    refreshTableBtn
  );
  tableWithToolbar(customToolbar);
}

//implement toolbar in table, change css of search
function tableWithToolbar(customToolbar) {
  let searchRow = document.getElementsByClassName("jexcel_filter")[0];
  searchRow.prepend(customToolbar);

  let searchContainer = searchRow.children[2];
  searchContainer.style.padding = "0px";
  searchContainer.style.display = "flex";
  searchContainer.style.flexDirection = "row";
  searchContainer.style.justifyContent = "flex-start";
  searchContainer.style.alignItems = "center";

  let searchField = searchContainer.children[0];
  searchField.style.padding = "6px";
  searchField.style.marginLeft = "5px";
  searchField.style.borderRadius = "3px";
  searchField.style.border = "1px solid gray";
  searchField.style.width = "200px";
  searchField.onfocus = noneOutlineBorder;
  searchField.addEventListener("focus", () => {
    jexcel.current.resetSelection();
  });

  let table = document.getElementsByClassName("jexcel_content")[0].children[0];
  table.style.border = "none";
}

//dynamically remove outline from search when it's in focus
function noneOutlineBorder() {
  this.style.border = "1px solid gray";
  this.style.outline = "none";
}

let employeesNameList = [];
let objectsNameList = [];
let rotateInterval;

//get modal, set loading icon, call two functions which request employee list and object list
//then call function which create fields in modal
async function addEmployeeInTable() {
  let modal = document.getElementById("modalContainer");
  let modalTitle = document.getElementById("modalTitle");
  let modalBody = document.getElementById("modalBody");

  modal.style.display = "flex";
  modalTitle.innerText = "Добавление сотрудника в таблицу";

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);

  await getEmployees(employeesNameList);
  await getObjects(objectsNameList);

  let inputsContainer = createContentInModal();
  modalBody.append(inputsContainer);
}

let angle = 0;
//rotate static loading icon with setInterval
function rotateImg() {
  angle += 10;
  let img = document.getElementById("preLoadingImg");
  img.style.transform = `rotateZ(${angle}deg)`;
}

//request employee list from server
async function getEmployees() {
  await fetch("/api/employees", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }

      return Promise.reject(response);
    })
    .then((data) => {
      employeesNameList = data;
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
      if (response.status === 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}

//request object list from server, clearInterval for loading icon and remove it
async function getObjects() {
  await fetch("/api/objects?active=true", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }

      return Promise.reject(response);
    })
    .then((data) => {
      objectsNameList = data;

      clearInterval(rotateInterval);
      let img = document.getElementById("preLoadingImg");
      img.remove();
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
      if (response.status === 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}

var currentSelect;
//create fields, buttons and empty list in modal
function createContentInModal() {
  let inputsContainer = document.createElement("div");
  inputsContainer.id = "inputsContainer";

  let employeeSelect = document.createElement("button");
  employeeSelect.id = "employeeSelect";
  employeeSelect.innerHTML = `Выберите сотрудника <span class="material-icons"> arrow_drop_down </span>`;
  employeeSelect.setAttribute("input-type", "employee");
  employeeSelect.onclick = createEmployeesList;
  employeeSelect.addEventListener("click", (e) => {
    currentSelect = e.target;
  });

  let objectSelect = document.createElement("button");
  objectSelect.id = "objectSelect";
  objectSelect.innerHTML = `По очереди выберите подопечных из списка <span class="material-icons"> arrow_drop_down </span>`;
  objectSelect.setAttribute("input-type", "object");
  objectSelect.disabled = true;
  objectSelect.classList.add("unacive-select");
  objectSelect.onclick = createObjectsList;
  objectSelect.addEventListener("click", (e) => {
    currentSelect = e.target;
  });

  let fieldOfSelection = document.createElement("div");
  fieldOfSelection.id = "fieldOfSelection";
  fieldOfSelection.style.display = "none";

  let btnsContainer = document.createElement("div");
  btnsContainer.id = "btnsContainer";

  let cancelBtn = document.createElement("button");
  cancelBtn.id = "cancelBtn";
  cancelBtn.type = "button";
  cancelBtn.innerText = "Отменить";
  cancelBtn.onclick = hideModal;

  let saveBtn = document.createElement("button");
  saveBtn.id = "saveBtn";
  saveBtn.type = "submit";
  saveBtn.innerText = "Сохранить";
  saveBtn.onclick = insertEmployeeIntoTable;

  btnsContainer.append(cancelBtn, saveBtn);

  inputsContainer.append(
    employeeSelect,
    objectSelect,
    fieldOfSelection,
    btnsContainer
  );
  return inputsContainer;
}

//when employee field is clicked, create search and list of employees
function createEmployeesList() {
  let inputsContainer = document.getElementById("inputsContainer");
  let employeeSelect = document.getElementById("employeeSelect");
  let objectSelect = document.getElementById("objectSelect");
  let fieldOfSelection = document.getElementById("fieldOfSelection");
  employeeSelect.disabled = true;
  employeeSelect.style.display = "none";
  objectSelect.style.display = "none";
  fieldOfSelection.style.display = "none";

  let employeeListContainer = document.createElement("div");
  employeeListContainer.id = "employeeListContainer";

  let employeeSearch = document.createElement("input");
  employeeSearch.id = "employeeSearch";
  employeeSearch.type = "text";
  employeeSearch.oninput = nameSearch;

  let employeeList = document.createElement("div");
  employeeList.id = "employeeList";

  renderListOfNames(employeesNameList, employeeList);

  let btnsContainer = document.getElementById("btnsContainer");
  let saveBtn = document.getElementById("saveBtn");

  let backBtn = document.createElement("button");
  backBtn.id = "backBtn";
  backBtn.innerText = "Назад";
  backBtn.onclick = returnBack;

  btnsContainer.insertBefore(backBtn, saveBtn);
  employeeListContainer.append(employeeSearch, employeeList);
  inputsContainer.prepend(employeeListContainer);
  employeeSearch.focus();
}

//when object field is clicked, create search and list of objects
function createObjectsList() {
  let inputsContainer = document.getElementById("inputsContainer");
  let employeeSelect = document.getElementById("employeeSelect");
  let objectSelect = document.getElementById("objectSelect");
  let fieldOfSelection = document.getElementById("fieldOfSelection");
  employeeSelect.disabled = true;
  employeeSelect.style.display = "none";
  objectSelect.style.display = "none";
  fieldOfSelection.style.display = "none";

  let objectListContainer = document.createElement("div");
  objectListContainer.id = "objectListContainer";

  let objectSearch = document.createElement("input");
  objectSearch.id = "objectSearch";
  objectSearch.type = "text";
  objectSearch.oninput = nameSearch;

  let objectList = document.createElement("div");
  objectList.id = "objectList";

  renderListOfNames(objectsNameList, objectList);

  let btnsContainer = document.getElementById("btnsContainer");
  let saveBtn = document.getElementById("saveBtn");

  let backBtn = document.createElement("button");
  backBtn.id = "backBtn";
  backBtn.innerText = "Назад";
  backBtn.onclick = returnBack;

  btnsContainer.insertBefore(backBtn, saveBtn);
  objectListContainer.append(objectSearch, objectList);
  inputsContainer.prepend(objectListContainer);

  objectSearch.focus();
}

//check what search is currently in use, and search through name list, add all results in new list
function nameSearch() {
  if (document.getElementById("employeeSearch") !== null) {
    var input = document.getElementById("employeeSearch");
    var container = document.getElementById("employeeList");
    var list = employeesNameList;
  }
  if (document.getElementById("objectSearch") !== null) {
    var input = document.getElementById("objectSearch");
    var container = document.getElementById("objectList");
    var list = objectsNameList;
  }
  let resultList = [];
  container.innerHTML = "";

  for (let i = 0; i < list.length; i++) {
    let currentName = list[i];
    if (
      currentName.name.toLowerCase().indexOf(input.value.toLowerCase()) > -1
    ) {
      resultList.push(currentName);
    }
  }
  renderListOfNames(resultList, container);
}

//render 50 first results from list
function renderListOfNames(list, container) {
  container.style.display = "none";
  list.slice(0, 50).forEach((r) => {
    let div = document.createElement("div");
    let anc = document.createElement("a");

    anc.innerText = " " + r.division_name;
    anc.classList.add("division-name-in-list");
    div.innerText = r.name;
    div.setAttribute("name", r.name);
    r.name_id
      ? div.setAttribute("name_id", r.name_id)
      : div.setAttribute("object_id", r.object_id);
    div.setAttribute("division", r.division_name);
    div.setAttribute("division_id", r.division);
    div.onclick = chosenName;

    div.append(anc);
    container.append(div);
  });
  container.style.display = "block";
}

//check what list is currently in use, and collect name value
//go back and set this value in the employee or object field,
//sends name object and current list to creation
function chosenName(e) {
  let input = null;
  let select = null;
  let element = e.currentTarget;
  let name = element.getAttribute("name");
  if (name == null) {
    return;
  }
  let objectSelect = document.getElementById("objectSelect");

  document.getElementById("employeeSearch")
    ? (input = document.getElementById("employeeSearch"))
    : (input = document.getElementById("objectSearch"));

  currentSelect.getAttribute("input-type") === "employee"
    ? (select = document.getElementById("employeeSelect"))
    : (select = document.getElementById("objectSelect"));

  input.value = name;
  returnBack();
  select.innerText = name;
  objectSelect.disabled = false;
  objectSelect.classList.remove("unacive-select");

  createListToAdd(element, select);
}

//check what list is currently in use,
//and put selected name into previously empty list on the right place(employee or object)
function createListToAdd(element, currentSelect) {
  let fieldOfSelection = document.getElementById("fieldOfSelection");
  fieldOfSelection.style.display = "flex";

  if (currentSelect.getAttribute("input-type") === "employee") {
    fieldOfSelection.childNodes[0]
      ? fieldOfSelection.childNodes[0].remove()
      : null;
    let employeeDiv = document.createElement("div");
    employeeDiv.innerText = element.getAttribute("name") + ":";
    employeeDiv.setAttribute("name", element.getAttribute("name"));
    employeeDiv.setAttribute("name_id", element.getAttribute("name_id"));
    employeeDiv.className = "employee-in-list-to-add";

    fieldOfSelection.prepend(employeeDiv);
  } else {
    let objectsInList = [...fieldOfSelection.children].slice(1);
    let flag = false;
    objectsInList.forEach((o) => {
      if (o.getAttribute("object_id") == element.getAttribute("object_id"))
        flag = true;
    });
    if (flag) return;

    let objectDiv = document.createElement("div");
    objectDiv.innerText = element.getAttribute("name");
    objectDiv.setAttribute("name", element.getAttribute("name"));
    objectDiv.setAttribute("object_id", element.getAttribute("object_id"));
    objectDiv.className = "objects-in-list-to-add";

    let anc = document.createElement("a");
    anc.innerText = "X";
    anc.className = "delete-object-in-list";
    anc.addEventListener("click", (e) => {
      let div = e.target.parentElement;
      div.remove();
    });

    objectDiv.appendChild(anc);
    fieldOfSelection.append(objectDiv);
  }
}

//clear lists, and return back employee and object fields, remove "return" btn
function returnBack() {
  currentSelect = null;
  let employeeSelect = document.getElementById("employeeSelect");
  let objectSelect = document.getElementById("objectSelect");
  employeeSelect.disabled = false;
  employeeSelect.style.display = "flex";
  objectSelect.style.display = "flex";

  let employeeListContainer = document.getElementById("employeeListContainer");
  let objectListContainer = document.getElementById("objectListContainer");
  employeeListContainer ? (employeeListContainer.innerHTML = "") : null;
  objectListContainer ? (objectListContainer.innerHTML = "") : null;

  let backBtn = document.getElementById("backBtn");
  backBtn.remove();
}

//add a new row to the table with selected employee and objects
function insertEmployeeIntoTable() {
  let elementsToAdd = document.getElementById("fieldOfSelection").children;
  if (elementsToAdd.length <= 1) {
    alertsToggle(
      "Выберите подопечных для добавления в таблицу!",
      "danger",
      4000
    );
    return;
  }
  let employeeName = elementsToAdd[0].getAttribute("name");
  let employeeId = elementsToAdd[0].getAttribute("name_id");

  [...elementsToAdd].slice(1).forEach((e) => {
    let objectName = e.getAttribute("name");
    let objectId = e.getAttribute("object_id");
    attendsTable.insertRow(
      [employeeName, employeeId, "", objectName, objectId],
      0,
      1
    );
  });

  hideModal();

  reMergeCells();

  if (localStorage.getItem("toggleComments") == "hide") {
    attendsTable.hideColumn(2);
  }
}

//call a function that collects request data
//and send it to the request function
function downloadXlsx(e) {
  let parameters = getTableParameters(e);
  $("#preLoadContainer")[0].style.display = "none";
  getXlsx(parameters);
}

//send a request with parameters to the server, and then dowload the excel table
function getXlsx(parameters) {
  let division =
    document.getElementById("divisionSelect").selectedOptions[0].innerText;

  let fileName = `${parameters.date_from}_${parameters.date_to}_${division}_Отчет.xlsx`;

  let xmlHttpRequest = new XMLHttpRequest();
  xmlHttpRequest.onreadystatechange = function () {
    var a;
    if (xmlHttpRequest.readyState === 4 && xmlHttpRequest.status === 200) {
      a = document.createElement("a");
      a.href = window.URL.createObjectURL(xmlHttpRequest.response);
      a.download = fileName;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
    }
  };
  xmlHttpRequest.open("POST", "/api/report/download");
  xmlHttpRequest.setRequestHeader("Content-Type", "application/json");
  xmlHttpRequest.responseType = "blob";
  xmlHttpRequest.send(JSON.stringify(parameters));
}

//check localStorage value, then hide or show the comments column, and change localStorage value
function toggleComments() {
  let toggleCommentsBtn = document.getElementById("toggleCommentsBtn");
  if (
    localStorage.getItem("toggleComments") == "show" ||
    localStorage.getItem("toggleComments") == null
  ) {
    toggleCommentsBtn.innerHTML = `<span class="material-icons">speaker_notes</span>`;
    attendsTable.hideColumn(2);
    attendsTable.options.columns[2].type = "hidden";
    localStorage.setItem("toggleComments", "hide");
  } else if (localStorage.getItem("toggleComments") == "hide") {
    toggleCommentsBtn.innerHTML = `<span class="material-icons">speaker_notes_off</span>`;
    attendsTable.showColumn(2);
    attendsTable.options.columns[2].type = "text";
    localStorage.setItem("toggleComments", "show");
  }
}

//get modal, call function that creates an empty table
//then call function that fills this table with data
function showDuplicates() {
  let modal = document.getElementById("modalContainer");
  let modalTitle = document.getElementById("modalTitle");
  let modalBody = document.getElementById("modalBody");

  modal.style.display = "flex";
  modalTitle.innerText = "Дубликаты посещений";

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);
  if (duplicateData.length == 0) {
    let div = document.createElement("div");
    div.innerText = "Данные о дубликатах отсутствуют";
    div.style.marginBottom = "20px";
    modalBody.append(div);

    clearInterval(rotateInterval);
    let img = document.getElementById("preLoadingImg");
    img.remove();
    return;
  }
  let duplicateTableContainer = createDuplicatesTable();
  modalBody.append(duplicateTableContainer);
  fillTableWithData(duplicateTableContainer);
}

//create an empty table for duplicates
function createDuplicatesTable() {
  let duplicateTableContainer = document.createElement("div");
  duplicateTableContainer.id = "duplicateTableContainer";

  let duplicateTable = document.createElement("table");
  duplicateTable.id = "duplicateTable";

  let thead = document.createElement("thead");
  let tr = document.createElement("tr");
  let thObj = document.createElement("th");
  thObj.innerText = "Подопечные";
  thObj.style.width = "235px";
  let thDate = document.createElement("th");
  thDate.innerText = "Дата";
  thDate.style.width = "100px";
  let thAmount = document.createElement("th");
  thAmount.innerText = "Кол-во";
  thAmount.style.width = "64px";
  let thEmp = document.createElement("th");
  thEmp.innerText = "Сотрудники";
  thEmp.style.width = "300px";
  thEmp.style.borderRight = "1px solid gray";

  tr.append(thObj, thDate, thAmount, thEmp);
  thead.append(tr);
  duplicateTable.append(thead);
  duplicateTableContainer.append(duplicateTable);
  return duplicateTableContainer;
}

//fill an empty table with data about duplicates
function fillTableWithData(duplicateTableContainer) {
  let count = 0;

  if (duplicateData.length > 4) {
    duplicateTableContainer.classList.add("scroll-table");
  }
  duplicateData.forEach((row, index) => {
    let tr = document.createElement("tr");
    let thObj = document.createElement("th");
    thObj.innerText = row.object;
    let thDate = document.createElement("th");
    thDate.innerText = row.date;
    let thAmount = document.createElement("th");
    thAmount.innerText = row.duration;
    let thEmp = document.createElement("th");
    thEmp.innerText = row.name;
    thEmp.style.borderRight = "1px solid gray";

    if (count === 0) {
      tr.className = "odd-row";
      count++;
    } else if (count === 1) {
      tr.className = "even-row";
      count = 0;
    }

    if (index == duplicateData.length - 1) {
      tr.classList.add("last-row");
    }

    tr.append(thObj, thDate, thAmount, thEmp);
    duplicateTableContainer.children[0].append(tr);
  });
  clearInterval(rotateInterval);
  let img = document.getElementById("preLoadingImg");
  img.remove();
}

//call the function that collects request parameters,
//then collect all additional parameters from table
function updateTable(e) {
  let arrayOfParameters = [];
  let parameters = getTableParameters(e);
  let table = attendsTable;
  arrayOfParameters.push(parameters, table);
  document.getElementById("attendsTable").style.display = "none";
  if (
    table.selectedCell != null ||
    table.selectedCell != undefined ||
    table.selectedCell != ""
  ) {
    let selectedCells = table.selectedCell;
    arrayOfParameters.push(selectedCells);
  }
  let search = document.getElementsByClassName("jexcel_search")[0];
  if (search.value != null || search.value != undefined) {
    let searchValue = search.value;
    arrayOfParameters.push(searchValue);
  }
  updateDataInTable(...arrayOfParameters);
}

//request table data from the server, and then replace the data in the table with new data
function updateDataInTable(parameters, table, selectedCells, searchValue) {
  $.ajax({
    url: "/api/report",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(parameters),
  })
    .done(function (data) {
      console.log("data: ", data);
      duplicateData = data.duplicated_attends;
      table.setData(data.horizontal_report.data);
      let newSearch = document.getElementsByClassName("jexcel_search")[0];
      reMergeCells();
      if (localStorage.getItem("toggleComments") == "hide") {
        attendsTable.hideColumn(2);
      }
      if (searchValue) {
        newSearch.value = searchValue;
        table.search(searchValue);
      }
      if (selectedCells) {
        table.updateSelectionFromCoords(...selectedCells);
        table.updateScroll();
      }
      $("#preLoadContainer")[0].style.display = "none";

      document.getElementById("attendsTable").style.display = "inline-block";
      document.getElementById("attendsTable").focus();
    })
    .fail(function (xhr, status, error) {
      let json = xhr.responseJSON;
      if (xhr.status == 422) {
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(json.detail, "danger", 6000);
      }
      if (xhr.status == 500) {
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}

//destroy merged cells in the table, and then merge cells again
function reMergeCells() {
  let table = attendsTable;
  table.destroyMerged();
  let columnData = table.getColumnData(0);
  let currentValue = columnData[0];
  let i = 0;
  for (i = 0; i < columnData.length; i++) {
    if (columnData[i] === "") {
      columnData[i] = currentValue;
    } else {
      currentValue = columnData[i];
    }
  }
  let toMergeCells = [];
  let startValue = columnData[0];
  let startIndex = 0;
  let endIndex = 0;

  for (i = 0; i < columnData.length; i++) {
    let value = columnData[i];
    if (value !== startValue) {
      if (i - startIndex > 1) {
        toMergeCells.push(["A" + String(startIndex + 1), i - startIndex]);
      }
      startValue = value;
      startIndex = i;
    }
    endIndex = i + 1;
  }
  if (endIndex - startIndex > 1) {
    toMergeCells.push(["A" + String(startIndex + 1), endIndex - startIndex]);
  }
  for (i in toMergeCells) {
    table.setMerge(toMergeCells[i][0], 0, toMergeCells[i][1]);
    let separator = table.getCell(toMergeCells[i][0]).parentElement.children;
    Array.from(separator).forEach((cell) => {
      cell.classList.add("higlight-separate");
    });
  }
}

const amountOfColumns = 6;
const frequencyColumnIndex = 5;

//all key events for table
function tableKeyEvents(e) {
  //table exist
  if (attendsTable) {
    //selection exist
    if (attendsTable.selectedCell) {
      //if selected row or colmn or header - return
      if (
        jexcel.current.selectedRow ||
        jexcel.current.selectedColumn ||
        jexcel.current.selectedHeader
      ) {
        return;
      }

      //gets slected DOM elements
      let selectedElements = attendsTable.highlighted;
      let toSetValue = [];
      let i = 0;

      //if only frequency column selected
      if (
        attendsTable.selectedCell[0] == frequencyColumnIndex &&
        attendsTable.selectedCell[2] == frequencyColumnIndex
      ) {
        if (e.code == "Delete") {
          //delete pressed
          for (i of selectedElements) {
            if (i.innerText != "") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, "");
        } else if (e.key >= 0 && e.key <= 4) {
          //key 0-4 pressed
          for (i of selectedElements) {
            if (i.innerText == "") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, e.key);
        }
      }
      //if selection starts from date cells
      if (jexcel.current.selectedCell[0] > amountOfColumns) {
        if (e.code == "Delete") {
          //key "Delete" pressed
          for (i of selectedElements) {
            if (i.innerText != "") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, "");
        } else if (e.code == "KeyD") {
          //key "В" pressed
          for (i of selectedElements) {
            if (i.innerText != "В") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, "В");
        } else if (e.code == "Comma") {
          //key "Б" pressed
          for (i of selectedElements) {
            if (i.innerText != "Б") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, "Б");
        } else if (e.code == "KeyJ") {
          //key "О" pressed
          for (i of selectedElements) {
            if (i.innerText != "О") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, "О");
        } else if (e.code == "KeyE") {
          //key "У" pressed
          for (i of selectedElements) {
            if (i.innerText != "У") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, "У");
        } else if (e.code == "KeyY") {
          //key "Н" pressed
          for (i of selectedElements) {
            if (i.innerText != "Н") toSetValue.push(i);
          }
          attendsTable.setValue(toSetValue, "Н");
        }
      }
    }
  }
  if (e.ctrlKey && e.code == "KeyR") {
    e.preventDefault();
    console.log(e);
    document.getElementById("refreshTableBtn").click();
  }
}
