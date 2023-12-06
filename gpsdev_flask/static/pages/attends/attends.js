import { alertsToggle } from "../../alerts.js";
import { hideModal } from "../../modal.js";
import { dictionary } from "../../translation_dict.js";

let attendsTable;
let currentRowOfTable;
let serverErrorTimer = 0;
let serverUnavailable = false;

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
let noPaymentsData = null;

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
      noPaymentsData = data.no_payments;
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

        onundo: (instance, obj) => {
          console.log(instance, obj);
          if (obj.action == "insertRow") {
            reMergeCells();
            return;
          }
          if (!obj || obj.action != "setValue") {
            return;
          }
          obj.records.forEach((r) => {
            let cell = attendsTable.getCellFromCoords(r.x, r.y);
            let x = parseInt(r.x);
            let y = parseInt(r.y);
            let value = r.oldValue;
            if (!["В", "Б", "О", "У", "Н", ""].includes(r.oldValue)) {
              value = "В";
            }
            getChangedStatementAndFrequencyParameters(
              instance,
              cell,
              x,
              y,
              value
            );
          });
        },
        onchange: getChangedStatementAndFrequencyParameters,
        updateTable: coloredTable,
        text: {
          search: "Поиск",
        },
        contextMenu: createContextMenu,
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
      if (xhr.status >= 500) {
        document.getElementById("requestBtn").disabled = false;
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
      if (xhr.status == 422) {
        document.getElementById("requestBtn").disabled = false;
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(json.detail, "danger", 6000);
      }
      if (xhr.status == 403) {
        document.getElementById("requestBtn").disabled = false;
        $("#preLoadContainer")[0].style.display = "none";
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
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

let copyOfJexcelCurrent;

function showModalInTable() {
  let modal = document.getElementById("modalContainer");
  modal.style.display = "flex";

  if (jexcel.current != null) {
    copyOfJexcelCurrent = jexcel.current;
    jexcel.current = null;
  }
}

document.addEventListener("modalClose", () => {
  if (copyOfJexcelCurrent != null) {
    jexcel.current = copyOfJexcelCurrent;
  }
  if (rotateInterval) {
    clearInterval(rotateInterval);
  }
  if (asyncFetchController) {
    asyncFetchController.abort();
    asyncFetchController = null;
  }
});

let asyncFetchController = null;

//get modal, set loading icon, call two functions which request employee list and object list
//then call function which create fields in modal
async function addEmployeeInTable() {
  let modalTitle = document.getElementById("modalTitle");
  let modalBody = document.getElementById("modalBody");

  modalBody.innerHTML = "";

  modalTitle.innerText = "Добавление сотрудника в таблицу";
  showModalInTable();

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);

  asyncFetchController = new AbortController();

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
  img ? (img.style.transform = `rotateZ(${angle}deg)`) : null;
}

//request employee list from server
async function getEmployees() {
  if (!asyncFetchController) return;
  await fetch("/api/employees", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: asyncFetchController.signal,
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

//request object list from server, clearInterval for loading icon and remove it
async function getObjects() {
  if (!asyncFetchController) return;
  await fetch("/api/objects?active=true", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: asyncFetchController.signal,
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
  objectSelect.classList.add("unactive-select");
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
  objectSelect.classList.remove("unactive-select");

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
  let modalTitle = document.getElementById("modalTitle");
  let modalBody = document.getElementById("modalBody");

  modalTitle.innerText = "Дубликаты посещений";
  showModalInTable();

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
      noPaymentsData = data.no_payments;
      table.destroyMerged();
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
      attendsTable.updateTable();
      document.getElementById("attendsTable").focus();
    })
    .fail(function (xhr, status, error) {
      let json = xhr.responseJSON;
      if (xhr.status == 422) {
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(json.detail, "danger", 6000);
      }
      if (xhr.status >= 500) {
        $("#preLoadContainer")[0].style.display = "none";
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
      cell.classList.add("highlight-separate");
    });
  }
  [...$("#attendsTable [data-x=6]")].forEach((cell) => {
    cell.classList.add("highlight-separate-right");
  });

  let newHistory = [];
  for (let i = 0; i < attendsTable.history.length; i++) {
    if (attendsTable.history[i].action != "setMerge") {
      newHistory.push(attendsTable.history[i]);
    }
  }
  attendsTable.history = newHistory;
  attendsTable.historyIndex = newHistory.length - 1 || -1;
  if (attendsTable.history.length == 1) attendsTable.historyIndex = 0;
}

const employeeNameColumnIndex = 0;
const employeeIdColumnIndex = 1;
const commentsColumnIndex = 2;
const objectNameColumnIndex = 3;
const objectIdColumnIndex = 4;
const frequencyColumnIndex = 5;
const incomeColumnIndex = 6;
const amountOfColumns = 6;

const cellsColors = {
  1: "#bbf5fc",
  2: "#b269fa",
  3: "#fa5c19",
  Б: "#b7e1cd",
  О: "#ffe599",
  У: "#aaaaaa",
  С: "#c27ba0",
  В: "#cfe2f3",
  "Н/Б": "#f88a8a",
  ПРОВ: "#ffa62c",
  "БОЛЬНИЧНЫЙ/ОТПУСК/УВОЛ.": "#fce5cd",
  no_payments: "#d8abc9",
  Н: "#cfd09e",
};

function coloredTable(instance, cell, col, row, val, label, cellName) {
  if (col == 3 || col > amountOfColumns) {
    if (Object.keys(cellsColors).includes(cell.innerText)) {
      cell.style.backgroundColor = cellsColors[cell.innerText];
    } else if (cell.innerText.includes(":")) {
      cell.style.backgroundColor = cellsColors["В"];
    } else if (cell.innerText > 3) {
      cell.style.backgroundColor = cellsColors["3"];
    } else if (val == "") cell.style.backgroundColor = "";
  } else if (col == 4 && noPaymentsData.includes(val)) {
    instance.jexcel.getCellFromCoords(3, row).style.backgroundColor =
      cellsColors["no_payments"];
  }
}

//all key events for table
function tableKeyEvents(e) {
  if (jexcel.current == null) return;
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
            let y = i.dataset.y;
            let objectId = attendsTable.getCellFromCoords(4, y).innerText;
            if (i.innerText != "В" && i.innerText != "Н/Б" && objectId != 1)
              toSetValue.push(i);
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
    document.getElementById("refreshTableBtn").click();
  }
}

let listOfChangedStatements = [];
let listOfChangedFrequencies = [];

let listOfStatementsToSend = [];
let listOfFrequenciesToSend = [];

let fetchStatementsPending = false;
let fetchFrequencyPending = false;

function getChangedStatementAndFrequencyParameters(
  instance,
  cell,
  x,
  y,
  value
) {
  if (x > amountOfColumns) {
    if (value == "С" || value == "ПРОВ") return;
    let date = attendsTable.getColumnOptions(x).title;
    let divisionId = parseInt(
      localStorage.getItem("previous-selected-division")
    );
    let employeeId = parseInt(attendsTable.getCellFromCoords(1, y).innerText);
    let objectId = parseInt(attendsTable.getCellFromCoords(4, y).innerText);
    if (value == "В" && objectId == 1) return;

    let parameters = {
      date: date,
      division: divisionId,
      name_id: employeeId,
      object_id: objectId,
      value: value,
    };

    listOfChangedStatements.push(parameters);
    console.log(listOfChangedStatements);
  } else if (x == frequencyColumnIndex) {
    let divisionId = parseInt(
      localStorage.getItem("previous-selected-division")
    );
    let employeeId = parseInt(attendsTable.getCellFromCoords(1, y).innerText);
    let objectId = parseInt(attendsTable.getCellFromCoords(4, y).innerText);

    value == "" ? (value = null) : null;

    let parameters = {
      division_id: divisionId,
      employee_id: employeeId,
      object_id: objectId,
      frequency: value,
    };

    listOfChangedFrequencies.push(parameters);
    console.log(listOfChangedFrequencies);
  }
}

setInterval(() => {
  if (fetchStatementsPending) return;
  if (!listOfStatementsToSend.length) {
    listOfStatementsToSend = [...listOfChangedStatements];
    listOfChangedStatements = [];
  }
  fetchStatementsPending = true;

  sendChangedStatements();
}, 1000);

setInterval(() => {
  if (fetchFrequencyPending) return;
  if (!listOfFrequenciesToSend.length) {
    listOfFrequenciesToSend = [...listOfChangedFrequencies];
    listOfChangedFrequencies = [];
  }
  fetchFrequencyPending = true;

  sendChangedFrequencies();
}, 1000);

function sendChangedStatements() {
  if (!listOfStatementsToSend.length) {
    fetchStatementsPending = false;
    return;
  }
  if (!window.navigator.onLine) {
    fetchStatementsPending = false;
    return;
  }
  fetch("/api/statements", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(listOfStatementsToSend),
  })
    .then((response) => {
      if (response.ok) {
        if (serverUnavailable) {
          alertsToggle(
            "Соединение с сервером восстанолено. Изменения сохранены!",
            "success",
            5000
          );
          serverUnavailable = false;
        }
        console.log("Изменения сохранены");
        listOfStatementsToSend = [];
        fetchStatementsPending = false;
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];

            fetchStatementsPending = false;
            console.log(newD);
          });
        });
      }
      if (response.status >= 500) {
        fetchStatementsPending = false;
        serverUnavailable = true;
        let currentSeconds = parseInt(new Date().getTime() / 1000);
        if (currentSeconds - serverErrorTimer >= 5 || serverErrorTimer == 0) {
          serverErrorTimer = currentSeconds;
          alertsToggle(
            "Ошибка сервера! Изменения не сохранены. Повторное подключение...",
            "danger",
            4000
          );
        }
      } else {
        fetchStatementsPending = false;
        console.log(response);
      }
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
}

window.addEventListener("offline", () => {
  serverUnavailable = true;
});

function sendChangedFrequencies() {
  if (!listOfFrequenciesToSend.length) {
    fetchFrequencyPending = false;
    return;
  }
  if (!window.navigator.onLine) {
    fetchFrequencyPending = false;
    return;
  }
  fetch("/api/frequency", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(listOfFrequenciesToSend),
  })
    .then((response) => {
      if (response.ok) {
        if (serverUnavailable) {
          alertsToggle(
            "Соединение с сервером восстанолено. Изменения сохранены!",
            "success",
            5000
          );
          serverUnavailable = false;
        }
        console.log("Изменения сохранены");
        listOfFrequenciesToSend = [];
        fetchFrequencyPending = false;
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            fetchFrequencyPending = false;
            console.log(newD);
          });
        });
      }
      if (response.status >= 500) {
        fetchFrequencyPending = false;
        serverUnavailable = true;
        let currentSeconds = parseInt(new Date().getTime() / 1000);
        if (currentSeconds - serverErrorTimer >= 5 || serverErrorTimer == 0) {
          serverErrorTimer = currentSeconds;
          alertsToggle(
            "Ошибка сервера! Изменения не сохранены. Повторное подключение...",
            "danger",
            4000
          );
        }
      }
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
}

$("#attendsTable")[0].addEventListener("dblclick", editComments);

function editComments(e) {
  let cellToChange = e.target;

  if (cellToChange.dataset.x == commentsColumnIndex) {
    let modalTitle = document.getElementById("modalTitle");
    let modalBody = document.getElementById("modalBody");

    modalTitle.innerText = "Комментарий";

    showModalInTable();

    let commentAreaContainer = document.createElement("div");
    commentAreaContainer.id = "commentAreaContainer";

    let commentArea = document.createElement("textarea");
    commentArea.id = "commentArea";
    commentArea.name = "comment";
    commentArea.cols = 48;
    commentArea.rows = 6;
    commentArea.maxLength = 250;
    commentArea.value = cellToChange.innerText;
    commentArea.dataset.x = cellToChange.dataset.x;
    commentArea.dataset.y = cellToChange.dataset.y;

    let symbolsCount = document.createElement("span");
    symbolsCount.id = "symbolsCount";
    symbolsCount.innerText = `${cellToChange.innerText.length}/250`;

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
    saveBtn.onclick = getComment;

    btnsContainer.append(cancelBtn, saveBtn);
    commentAreaContainer.append(commentArea, symbolsCount, btnsContainer);
    modalBody.append(commentAreaContainer);

    commentArea.addEventListener("keyup", (e) => {
      symbolsCount.innerText = `${e.target.value.length}/250`;
    });
    commentArea.focus();
  }
}

function getComment() {
  let commentArea = document.getElementById("commentArea");
  let x = commentArea.dataset.x;
  let y = commentArea.dataset.y;
  let divisionId = parseInt(localStorage.getItem("previous-selected-division"));
  let employeeId = parseInt(attendsTable.getCellFromCoords(1, y).innerText);
  let objectId = parseInt(attendsTable.getCellFromCoords(4, y).innerText);

  let parameters = {
    comment: commentArea.value,
    division_id: divisionId,
    employee_id: employeeId,
    object_id: objectId,
  };
  sendComment(parameters, x, y);
}

function sendComment(parameters, x, y) {
  fetch("/api/comment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.ok) {
        attendsTable.setValueFromCoords(x, y, parameters.comment.trim());
        hideModal();
        alertsToggle("Комментарий обновлен!", "success", 2000);
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            console.log(newD);
            alertsToggle(newD, "danger", 5000);
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

$("#attendsTable")[0].addEventListener("dblclick", editIncome);

function editIncome(e) {
  let cellToChange = e.target;

  if (cellToChange.dataset.x == incomeColumnIndex) {
    let modalTitle = document.getElementById("modalTitle");
    let modalBody = document.getElementById("modalBody");

    modalTitle.innerText = "Программа ПСУ";

    showModalInTable();

    let incomeFormContainer = document.createElement("div");
    incomeFormContainer.id = "incomeFormContainer";

    let incomeFieldContainer = document.createElement("div");
    incomeFieldContainer.id = "incomeFieldContainer";

    let incomeFieldLabel = document.createElement("label");
    incomeFieldLabel.id = "incomeFieldLabel";
    incomeFieldLabel.htmlFor = "";
    incomeFieldLabel.innerText = "Введите сумму (число с точкой):";

    let incomeField = document.createElement("input");
    incomeField.id = "incomeField";
    incomeField.type = "number";
    incomeField.step = "any";
    incomeField.value = cellToChange.innerText;
    incomeField.dataset.x = cellToChange.dataset.x;
    incomeField.dataset.y = cellToChange.dataset.y;

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
    saveBtn.onclick = getIncome;

    btnsContainer.append(cancelBtn, saveBtn);

    incomeFieldContainer.append(incomeFieldLabel, incomeField);
    incomeFormContainer.append(incomeFieldContainer, btnsContainer);
    modalBody.append(incomeFormContainer);

    incomeField.focus();
  }
}

function getIncome() {
  let incomeField = document.getElementById("incomeField");
  let x = incomeField.dataset.x;
  let y = incomeField.dataset.y;
  let objectId = parseInt(attendsTable.getCellFromCoords(4, y).innerText);

  let value = incomeField.value;

  value == "" ? (value = null) : null;

  let parameters = {
    income: value,
  };
  sendIncome(parameters, objectId, x, y);
}

function sendIncome(parameters, objectId, x, y) {
  fetch(`/api/objects/${objectId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.ok) {
        attendsTable.getColumnData(objectIdColumnIndex).forEach((id, index) => {
          if (id == objectId) {
            attendsTable.setValueFromCoords(
              incomeColumnIndex,
              index,
              parameters.income
            );
          }
        });
        hideModal();
        alertsToggle("Доход был обновлен!", "success", 2000);
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            alertsToggle(newD, "danger", 5000);
            console.log(newD);
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

$("#attendsTable")[0].addEventListener("mouseover", (e) => {
  let currentCell = e.target;
  if (currentCell.dataset.x == commentsColumnIndex) {
    currentCell.title = currentCell.innerText;
  } else if (currentCell.dataset.x == incomeColumnIndex) {
    currentCell.title = currentCell.innerText + "\n*Двойной клик для изменения";
  }
});

function createContextMenu(object, x, y, e) {
  let contextMenuList = [];
  let servesLabelsList = { "Н/Б": [], С: [], ПРОВ: [] };
  let selectedCoord = attendsTable.selectedCell;
  let oneCell =
    selectedCoord[0] == selectedCoord[2] &&
    selectedCoord[1] == selectedCoord[3];

  let asIds = true;
  let rows = jexcel.current.getSelectedRows(asIds);
  let columns = attendsTable.getSelectedColumns();
  for (let i = 0; i < rows.length; i++) {
    let row = rows[i];
    for (let j = 0; j < columns.length; j++) {
      let column = columns[j];
      let label = attendsTable.getLabelFromCoords(column, row);
      let cell = attendsTable.getCellFromCoords(column, row);
      if (["Н/Б", "С", "ПРОВ"].includes(label)) {
        let nameId = parseInt(attendsTable.getCellFromCoords(1, row).innerText);
        let objectId = parseInt(
          attendsTable.getCellFromCoords(4, row).innerText
        );
        let date = attendsTable.getColumnOptions(column).title;
        let object = {
          cell: cell,
          name_id: nameId,
          object_id: objectId,
          date: date,
        };
        servesLabelsList[label].push(object);
      }
    }
  }

  if (x > amountOfColumns && y && oneCell) {
    let ctxmObject = {
      title: "Перемещения и отчет",
      onclick: () => {
        contextMenuOneEmployeeMap(object, x, y, e);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  // добавление одной служебки
  if (x > amountOfColumns && y && servesLabelsList["Н/Б"].length && oneCell) {
    let ctxmObject = {
      title: "Служебки -> Добавить",
      onclick: () => {
        contextMenuServesToAdd(servesLabelsList["Н/Б"]);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  // добавление нескольких служебок
  if (x > amountOfColumns && y && servesLabelsList["Н/Б"].length && !oneCell) {
    let ctxmObject = {
      title: "Служебки -> Добавить",
      onclick: () => {
        contextMenuServesToAdd(servesLabelsList["Н/Б"]);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  // просмотр одной или нескольких служебок
  if (
    x > amountOfColumns &&
    y &&
    (servesLabelsList["ПРОВ"].length || servesLabelsList["С"].length)
  ) {
    let ctxmObject = {
      title: "Служебки -> Просмотреть",
      onclick: () => {
        let servesToWatch = [
          ...servesLabelsList["ПРОВ"],
          ...servesLabelsList["С"],
        ];
        contextMenuServesToWatch(servesToWatch);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  // удаление одной или нескольких служебок
  if (
    x > amountOfColumns &&
    y &&
    (servesLabelsList["ПРОВ"].length || servesLabelsList["С"].length)
  ) {
    let ctxmObject = {
      title: "Служебки -> Удалить",
      onclick: () => {
        let servesToDelete = [
          ...servesLabelsList["ПРОВ"],
          ...servesLabelsList["С"],
        ];
        contextMenuServesToDelete(servesToDelete);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  // подтверждение одной или нескольких служебок
  if (
    x > amountOfColumns &&
    y &&
    servesLabelsList["ПРОВ"].length &&
    localStorage.getItem("rang-id") <= 2
  ) {
    let ctxmObject = {
      title: "Служебки -> Подтвердить",
      onclick: () => {
        contextMenuServesToApprove(servesLabelsList["ПРОВ"]);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  // добавление подопечного к сотруднику
  if (x == employeeNameColumnIndex && y && oneCell) {
    let ctxmObject = {
      title: "Добавить подопечного",
      onclick: () => {
        let lastRowOfEmployee = attendsTable.getSelectedRows(true).pop();
        contextMenuAddObject(object, x, y, e, lastRowOfEmployee);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  // просмотр подопечного
  if (x == objectNameColumnIndex && y && oneCell) {
    let ctxmObject = {
      title: "Данные о подопечном",
      onclick: () => {
        contextMenuCreateObjectForm(object, x, y, e);
      },
    };
    contextMenuList.push(ctxmObject);
  }

  return contextMenuList;
}

async function contextMenuOneEmployeeMap(object, x, y, e) {
  let parameters = getDataToMapRequest(x, y);
  let employeeName = attendsTable.getCellFromCoords(0, y).innerText;
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";
  clearInterval(rotateInterval);

  modalTitle.innerText = `Перемещения и Отчет: ${employeeName} (${parameters.date})`;

  showModalInTable();

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);

  let data = await getMap(parameters);
  console.log(data);
  if (data == null) {
    hideModal();
    preLoadingImg.remove();
    return;
  }
  drawMap(data, employeeName, parameters);
}

function getDataToMapRequest(x, y) {
  let divisionId = parseInt(localStorage.getItem("previous-selected-division"));
  let employeeId = parseInt(attendsTable.getCellFromCoords(1, y).innerText);
  let date = attendsTable.getColumnOptions(x).title;

  let parameters = {
    name_id: employeeId,
    division: divisionId,
    date: date,
  };

  return parameters;
}

async function getMap(parameters) {
  let result;
  await fetch("/api/one-employee-report", {
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
      result = data;
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            alertsToggle(newD, "danger", 5000);
            console.log(newD);
            result = null;
          });
        });
      }
      if (response.status >= 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
        result = null;
      }
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
  return result;
}

function drawMap(data, employeeName, parameters) {
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";
  clearInterval(rotateInterval);

  modalTitle.innerText = `Перемещения и Отчет: ${employeeName} (${parameters.date})`;

  showModalInTable();

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);

  let modalContent = createMapAndReport(data);
  modalBody.append(modalContent);

  let horizontalPartContainer = document.getElementById(
    "horizontalPartContainer"
  );

  let reportBtn = document.getElementById("reportBtn");
  let reportPartContainer = createReportTable();
  fillReportWithData(reportPartContainer, data);
  if (reportBtn.dataset.toggleReport == "false") {
    reportPartContainer.style.display = "none";
    reportPartContainer.className = "report-container-hide";
  } else if (reportBtn.dataset.toggleReport == "true" && data.report) {
    reportPartContainer.style.display = "block";
    reportPartContainer.className = "report-container-show";
  }

  horizontalPartContainer.append(reportPartContainer);

  let analysisBtn = document.getElementById("analysisBtn");
  let analysisPartContainer = createAnalysisTable();
  fillAnalysisWithData(analysisPartContainer, data);
  if (analysisBtn.dataset.toggleAnalysis == "false") {
    analysisPartContainer.style.display = "none";
    analysisPartContainer.className = "analysis-container-hide";
  } else if (analysisBtn.dataset.toggleAnalysis == "true" && data.analytics) {
    analysisPartContainer.style.display = "block";
    analysisPartContainer.className = "analysis-container-show";
  }

  contentContainer.append(analysisPartContainer);

  clearInterval(rotateInterval);
  preLoadingImg.remove();
}

function createMapAndReport(data) {
  if (data.no_movements) {
    alertsToggle(
      "Недостаточно локаций, чтобы отобразить перемещения на карте!",
      "info",
      5000
    );
  }

  let contentContainer = document.createElement("div");
  contentContainer.id = "contentContainer";

  let horizontalPartContainer = document.createElement("div");
  horizontalPartContainer.id = "horizontalPartContainer";

  let mapContainer = document.createElement("div");
  mapContainer.id = "mapContainer";
  mapContainer.innerHTML = data.map;

  let reportBtn = document.createElement("button");
  reportBtn.id = "reportBtn";
  reportBtn.innerText = "Отчет";
  reportBtn.onclick = toggleReportInModal;
  if (localStorage.getItem("toggleReport") == "true") {
    reportBtn.dataset.toggleReport = true;
  } else {
    reportBtn.dataset.toggleReport = false;
  }

  let analysisBtn = document.createElement("button");
  analysisBtn.id = "analysisBtn";
  analysisBtn.innerText = "Анализ";
  analysisBtn.onclick = toggleAnalysisInModal;
  if (localStorage.getItem("toggleAnalysis") == "true") {
    analysisBtn.dataset.toggleAnalysis = true;
  } else {
    analysisBtn.dataset.toggleAnalysis = false;
  }
  mapContainer.prepend(reportBtn, analysisBtn);
  horizontalPartContainer.append(mapContainer);
  contentContainer.append(horizontalPartContainer);

  return contentContainer;
}

function createReportTable() {
  let reportPartContainer = document.createElement("div");
  reportPartContainer.id = "reportPartContainer";

  let reportTable = document.createElement("table");
  reportTable.id = "reportTable";

  let thead = document.createElement("thead");
  let tr = document.createElement("tr");

  let thObj = document.createElement("th");
  thObj.innerText = "Подопечные";
  thObj.style.width = "235px";

  let thVisitsAmount = document.createElement("th");
  thVisitsAmount.innerText = "Всего посещ.";
  thVisitsAmount.style.width = "58px";

  let thVisits = document.createElement("th");
  thVisits.innerText = "Номер посещ.";
  thVisits.style.width = "58px";

  let thTime = document.createElement("th");
  thTime.innerText = "Время";
  thTime.style.width = "64px";

  let thDuration = document.createElement("th");
  thDuration.innerText = "Длит.";
  thDuration.style.width = "64px";
  thDuration.style.borderRight = "1px solid gray";

  tr.append(thObj, thVisitsAmount, thVisits, thTime, thDuration);
  thead.append(tr);
  reportTable.append(thead);
  reportPartContainer.append(reportTable);
  return reportPartContainer;
}

function fillReportWithData(reportPartContainer, data) {
  let count = 0;

  if (!data.report) {
    reportPartContainer.style.display = "none";
    let reportBtn = document.getElementById("reportBtn");
    reportBtn.disabled = true;
    reportBtn.classList.add("unactive-select");
    reportBtn.style.backgroundColor = "rgb(168 164 164)";
    reportBtn.style.color = "rgb(226 219 219)";
    reportBtn.title = "Не было посещений";
    return;
  }
  if (data.report.length > 18) {
    reportPartContainer.classList.add("scroll-table");
  }

  // Все ПСУ в списке data.report упорядочены.
  // Если мы один раз встретили объект, значит, если он будет повторяться, то мы встретим его следующим в списке.
  // Когда мы встречаем новый объект - назначаем countRepeatObjects в соответствии с его цифрой в параметре row.attends_sum.
  // А потом уменьшаем countRepeatObjects на 1 (это неважно, главное не оставить тем же)
  // В то же время, если previousObject не совпадает с текущей строкой, то мы обнуляем countRepeatObjects
  // до цифры из row.attends_sum.
  let countRepeatObjects = 0;
  let previousObject = "";
  data.report.forEach((row, index) => {
    let tr = document.createElement("tr");
    // Тот же объект, что и был в предыдущей итерации?
    let samePreviousObject = row.object == previousObject;
    // Если другой, то нужно обновить countRepeatObjects!
    if (!samePreviousObject) countRepeatObjects = row.attends_sum;

    let thObj = document.createElement("th");
    thObj.innerText = row.object;

    let thVisitsAmount = document.createElement("th");
    thVisitsAmount.innerText = row.attends_sum;

    let thVisits = document.createElement("th");
    thVisits.innerText = row.attend_number;

    let thTime = document.createElement("th");
    thTime.innerText = row.time;

    let thDuration = document.createElement("th");
    thDuration.innerText = row.duration;
    thDuration.style.borderRight = "1px solid gray";

    if (count === 0) {
      tr.className = "odd-row";
      count++;
    } else if (count === 1) {
      tr.className = "even-row";
      count = 0;
    }

    if (index == data.report.length - 1) {
      tr.classList.add("last-row");
    }

    // Если эти параметры совпадают, то мы 100% встретили новый объект, и нужно проставить rowSpan, так как
    // в следующих строках мы будем игнорировать 2 первых столбца, пока не встретим новый объект
    if (countRepeatObjects == row.attends_sum) {
      countRepeatObjects--;
      thObj.rowSpan = row.attends_sum;
      thVisitsAmount.rowSpan = row.attends_sum;
      tr.append(thObj, thVisitsAmount, thVisits, thTime, thDuration);
    } else if (countRepeatObjects != row.attends_sum) {
      tr.append(thVisits, thTime, thDuration);
    }

    previousObject = row.object;
    reportPartContainer.children[0].append(tr);
  });
}

function createAnalysisTable() {
  let analysisPartContainer = document.createElement("div");
  analysisPartContainer.id = "analysisPartContainer";

  let analysisTable = document.createElement("table");
  analysisTable.id = "analysisTable";

  let thead = document.createElement("thead");
  let tr = document.createElement("tr");

  let thStatus = document.createElement("th");
  thStatus.innerText = "Состояние";
  thStatus.style.width = "58px";

  let thTime = document.createElement("th");
  thTime.innerText = "Время";
  thTime.style.width = "64px";

  let thDuration = document.createElement("th");
  thDuration.innerText = "Длит.";
  thDuration.style.width = "64px";
  thDuration.style.borderRight = "1px solid gray";

  tr.append(thStatus, thTime, thDuration);
  thead.append(tr);
  analysisTable.append(thead);
  analysisPartContainer.append(analysisTable);
  return analysisPartContainer;
}

function fillAnalysisWithData(analysisPartContainer, data) {
  let count = 0;

  if (!data.analytics) {
    analysisPartContainer.style.display = "none";
    let analysisBtn = document.getElementById("analysisBtn");
    analysisBtn.disabled = true;
    analysisBtn.classList.add("unactive-select");
    analysisBtn.style.backgroundColor = "rgb(168 164 164)";
    analysisBtn.style.color = "rgb(226 219 219)";
    analysisBtn.title = "Не было посещений";
    return;
  }
  if (data.analytics.length > 3) {
    analysisPartContainer.classList.add("scroll-table");
  }
  data.analytics.forEach((row, index) => {
    let tr = document.createElement("tr");

    let thStatus = document.createElement("th");
    thStatus.innerText = row.status == true ? "Вкл." : "Выкл.";

    let thTime = document.createElement("th");
    thTime.innerText = `${row.start.slice(0, 5)}-${row.end.slice(0, 5)}`;

    let thDuration = document.createElement("th");
    thDuration.innerText = row.duration;
    thDuration.style.borderRight = "1px solid gray";

    if (count === 0) {
      tr.className = "odd-row";
      count++;
    } else if (count === 1) {
      tr.className = "even-row";
      count = 0;
    }

    if (index == data.analytics.length - 1) {
      tr.classList.add("last-row");
    }

    tr.append(thStatus, thTime, thDuration);
    analysisPartContainer.children[0].append(tr);
  });
}

function toggleReportInModal() {
  let reportBtn = document.getElementById("reportBtn");
  let reportPartContainer = document.getElementById("reportPartContainer");

  if (reportBtn.dataset.toggleReport == "false") {
    reportPartContainer.style.width = "500px";
    reportPartContainer.style.display = "block";
    reportPartContainer.style.marginLeft = "10px";
    reportPartContainer.style.transition = "all 0.8s";
    reportPartContainer.style.opacity = 1;
    setTimeout(() => {
      reportPartContainer.style.flex = 1;
    }, 1);

    localStorage.setItem("toggleReport", true);
    reportBtn.dataset.toggleReport = true;
  } else if (reportBtn.dataset.toggleReport == "true") {
    reportPartContainer.style.opacity = 0;
    reportPartContainer.style.flex = 0;
    reportPartContainer.style.width = "0px";
    reportPartContainer.style.marginLeft = "0px";
    setTimeout(() => {
      reportPartContainer.style.display = "none";
    }, 800);

    localStorage.setItem("toggleReport", false);
    reportBtn.dataset.toggleReport = false;
  }
}

function toggleAnalysisInModal() {
  let analysisBtn = document.getElementById("analysisBtn");
  let analysisPartContainer = document.getElementById("analysisPartContainer");

  if (analysisBtn.dataset.toggleAnalysis == "false") {
    analysisPartContainer.style.height = "300px";
    analysisPartContainer.style.display = "block";
    analysisPartContainer.style.marginTop = "10px";
    analysisPartContainer.style.transition = "all 0.8s";
    analysisPartContainer.style.opacity = 1;
    setTimeout(() => {
      analysisPartContainer.style.flex = 2;
    }, 1);

    localStorage.setItem("toggleAnalysis", true);
    analysisBtn.dataset.toggleAnalysis = true;
  } else if (analysisBtn.dataset.toggleAnalysis == "true") {
    analysisPartContainer.style.opacity = 0;
    analysisPartContainer.style.flex = 0;
    analysisPartContainer.style.height = "0px";
    analysisPartContainer.style.marginTop = "0px";
    setTimeout(() => {
      analysisPartContainer.style.display = "none";
    }, 800);

    localStorage.setItem("toggleAnalysis", false);
    analysisBtn.dataset.toggleAnalysis = false;
  }
}

//create addresses container
let addressOuterContainer = document.createElement("div");
addressOuterContainer.id = "addressOuterContainer";
addressOuterContainer.style.display = "none";

let addressContainer = document.createElement("div");
addressContainer.id = "addressContainer";

addressOuterContainer.append(addressContainer);

function contextMenuServesToAdd(servesList) {
  console.log(servesList);
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";

  modalTitle.innerText = `Добавление служебных записок`;

  showModalInTable();

  let modalForm = createServeModalForm(servesList);

  addressContainer.innerHTML = "";
  modalForm.append(addressOuterContainer);
  modalBody.append(modalForm);
}

// create modal form container
let modalForm = document.createElement("form");
modalForm.id = "modalForm";
modalForm.autocomplete = "off";
modalForm.setAttribute("onSubmit", "return false");

function createServeModalForm(servesList) {
  let serveReasonContainer = document.createElement("div");
  serveReasonContainer.id = "serveReasonContainer";

  let serveReasonLabel = document.createElement("label");
  serveReasonLabel.id = "serveReasonLabel";
  serveReasonLabel.innerText = "Причина служебной записки:";
  serveReasonLabel.htmlFor = "serveReasonField";

  let serveReasonField = document.createElement("input");
  serveReasonField.id = "serveReasonField";
  serveReasonField.type = "text";
  serveReasonField.required = true;

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
  saveBtn.addEventListener("click", () => {
    getServeParameters(servesList);
  });

  serveReasonContainer.append(serveReasonLabel, serveReasonField);

  btnsContainer.append(cancelBtn, saveBtn);
  modalForm.append(serveReasonContainer, btnsContainer);

  if (servesList.length == 1) {
    let serveAddressContainer = document.createElement("div");
    serveAddressContainer.id = "serveAddressContainer";

    let serveAddressLabel = document.createElement("label");
    serveAddressLabel.id = "serveAddressLabel";
    serveAddressLabel.innerText = "Адрес (опционально):";
    serveAddressLabel.htmlFor = "serveAddressField";

    let serveAddressField = document.createElement("input");
    serveAddressField.id = "serveAddressField";
    serveAddressField.type = "text";
    serveAddressField.addEventListener("input", addressType);

    let switchAddressContainer = document.createElement("div");
    switchAddressContainer.id = "switchAddressContainer";

    let switchAddressLabelName = document.createElement("label");
    switchAddressLabelName.id = "switchAddressLabelName";
    switchAddressLabelName.innerText = "Изменить источник адресов: ";

    let switchAddressLabel = document.createElement("label");
    switchAddressLabel.id = "switchAddressLabel";

    let switchAddressBtn = document.createElement("input");
    switchAddressBtn.id = "switchAddressBtn";
    switchAddressBtn.type = "checkbox";
    if (localStorage.getItem("address-sorce") === "1") {
      switchAddressBtn.checked = false;
    } else if (localStorage.getItem("address-sorce") === "2") {
      switchAddressBtn.checked = true;
    } else {
      switchAddressBtn.checked = true;
    }

    let switchAddressSpan = document.createElement("span");
    switchAddressSpan.id = "switchAddressSpan";
    switchAddressSpan.onclick = switchAddress;

    switchAddressLabel.append(switchAddressBtn, switchAddressSpan);
    switchAddressContainer.append(switchAddressLabelName, switchAddressLabel);
    serveAddressContainer.append(
      serveAddressLabel,
      serveAddressField,
      switchAddressContainer
    );
    modalForm.insertBefore(serveAddressContainer, btnsContainer);
  }

  if (localStorage.getItem("rang-id") <= 2) {
    let serveConfirmContainer = document.createElement("div");
    serveConfirmContainer.id = "serveConfirmContainer";

    let serveConfirmLabel = document.createElement("label");
    serveConfirmLabel.id = "serveConfirmLabel";
    serveConfirmLabel.innerText = "Подтвердить служебную записку:";
    serveConfirmLabel.htmlFor = "serveConfirmField";

    let serveConfirmField = document.createElement("input");
    serveConfirmField.id = "serveConfirmField";
    serveConfirmField.type = "checkbox";

    serveConfirmContainer.append(serveConfirmLabel, serveConfirmField);
    modalForm.insertBefore(serveConfirmContainer, btnsContainer);
  }

  return modalForm;
}

function switchAddress() {
  let checkbox = document.getElementById("switchAddressBtn");
  if (!checkbox.checked) {
    localStorage.setItem("address-sorce", "2");
  } else if (checkbox.checked) {
    localStorage.setItem("address-sorce", "1");
  }
}

let lat;
let lon;

// when user clicks on the one of addresses
// get its value and append to input value,
// set attributes lat and lon
// then hide addresses container
function getOption(e) {
  let addressInput = document.getElementById("serveAddressField");
  let selectedOp = document.getElementById(e.target.id);
  lat = selectedOp.getAttribute("lat");
  lon = selectedOp.getAttribute("lon");
  addressInput.value = selectedOp.innerText;
  addressInput.setAttribute("lat", lat);
  addressInput.setAttribute("lon", lon);
  addressOuterContainer.style.display = "none";
  addressContainer.innerHTML = "";
  lat = "";
  lon = "";

  let serveConfirmLabel = document.getElementById("serveConfirmLabel");
  serveConfirmLabel.style.color = "rgb(157 157 157)";
  serveConfirmLabel.style.cursor = "no-drop";

  let serveConfirmField = document.getElementById("serveConfirmField");
  serveConfirmField.disabled = true;
  serveConfirmField.style.cursor = "no-drop";
}

// looking address from api, when found, all match addresses
// show in list
// list shows under the input
function getAddressList() {
  let addressInput = document.getElementById("serveAddressField");
  let adValue = addressInput.value;
  if (adValue == "") {
    addressOuterContainer.style.display = "none";
    addressContainer.innerHTML = "";
    return;
  }
  let url;

  url =
    localStorage.getItem("address-sorce") === "1"
      ? `api/address-lookup/google/${adValue}`
      : `api/address-lookup/${adValue}`;
  fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }

      return Promise.reject(response);
    })
    .then((data) => {
      let inputRect = addressInput.getBoundingClientRect();
      let left = inputRect.left;
      let bottom = inputRect.bottom;

      addressOuterContainer.style.left = left + "px";
      addressOuterContainer.style.top = bottom + "px";
      addressOuterContainer.style.display = "block";
      addressContainer.innerHTML = "";

      data.forEach((ad, index) => {
        if (adValue === ad.display_name) {
          return;
        }
        let op = document.createElement("div");
        op.className = "address-options";
        op.id = "address" + index;
        op.setAttribute("lat", ad.lat);
        op.setAttribute("lon", ad.lon);
        op.onclick = getOption;
        op.innerText = ad.display_name;

        addressContainer.append(op);
      });
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

// listen of input address, reset timeout on sending address
// every time, when input value changes
let time;
function addressType() {
  let addressInput = document.getElementById("serveAddressField");
  if (addressInput.hasAttribute("lat") && addressInput.hasAttribute("lon")) {
    addressInput.removeAttribute("lat");
    addressInput.removeAttribute("lon");

    let serveConfirmLabel = document.getElementById("serveConfirmLabel");
    serveConfirmLabel.style.color = "black";
    serveConfirmLabel.style.cursor = "pointer";

    let serveConfirmField = document.getElementById("serveConfirmField");
    serveConfirmField.disabled = false;
    serveConfirmField.style.cursor = "pointer";
  }
  clearTimeout(time);
  time = setTimeout(getAddressList, 500);
}

// check and change addresses position
function addressesPosition() {
  let addressInput = document.getElementById("serveAddressField");
  if (addressInput == null || addressInput == undefined) {
    return;
  }
  let inputRect = addressInput.getBoundingClientRect();
  let left = inputRect.left;
  let bottom = inputRect.bottom;
  if (addressInput.value == "") {
    return;
  }
  if (
    left == addressOuterContainer.style.left &&
    bottom == addressOuterContainer.style.top
  ) {
    return;
  }
  if (
    left != addressOuterContainer.style.left ||
    bottom != addressOuterContainer.style.top
  ) {
    addressOuterContainer.style.left = left + "px";
    addressOuterContainer.style.top = bottom + "px";
  }
}

window.addEventListener("resize", addressesPosition);

function getServeParameters(servesList) {
  let addressField = document.getElementById("serveAddressField");
  let address;
  addressField ? (address = addressField.value) : (address = null);
  let lat;
  addressField ? (lat = addressField.getAttribute("lat")) : null;
  let lon;
  addressField ? (lon = addressField.getAttribute("lon")) : null;
  let divisionId = parseInt(localStorage.getItem("previous-selected-division"));

  let comment = document.getElementById("serveReasonField").value;
  let approval = document.getElementById("serveConfirmField").checked;

  if (comment == "") {
    return;
  }

  let parameters;

  if (address == "" || address == null) {
    if (servesList.length == 1) {
      let nameId = servesList[0].name_id;
      let objectId = servesList[0].object_id;
      let date = servesList[0].date;

      console.log("one serve");
      parameters = {
        name_id: nameId,
        object_id: objectId,
        date: date,
        comment: comment,
      };
    } else {
      console.log("many serves");
      parameters = [];
      servesList.forEach((s) => {
        let nameId = s.name_id;
        let objectId = s.object_id;
        let date = s.date;

        let parametersObject = {
          name_id: nameId,
          object_id: objectId,
          date: date,
          comment: comment,
        };
        parameters.push(parametersObject);
      });
    }

    if (localStorage.getItem("rang-id") >= 2) {
      alertsToggle(
        "Подтверждение служебных записок вам недоступно!",
        "danger",
        5000
      );
      return;
    } else if (localStorage.getItem("rang-id") <= 2) {
      if (servesList.length == 1) {
        approval == true
          ? (parameters["approval"] = 1)
          : (parameters["approval"] = 3);
      } else {
        parameters.forEach((o) => {
          approval == true ? (o["approval"] = 1) : (o["approval"] = 3);
        });
      }
    }
  } else if (address?.length && lat != null && lon != null) {
    let nameId = servesList[0].name_id;
    let objectId = servesList[0].object_id;
    let date = servesList[0].date;

    console.log("one serve with address");
    parameters = {
      name_id: nameId,
      object_id: objectId,
      division: divisionId,
      date: date,
      latitude: lat,
      longitude: lon,
      comment: comment,
      address: address,
    };
  } else {
    alertsToggle("Выберите адрес или очистите поле с адресом!", "danger", 6000);
    return;
  }
  sendServe(parameters, servesList);
}

function sendServe(parameters, servesList) {
  let url;
  if (parameters.address != undefined) {
    url = "/api/serves/with-coordinates";
  } else {
    if (servesList.length == 1) {
      url = "/api/serves";
      parameters = [parameters];
    } else {
      url = "/api/serves";
    }
  }
  console.log(parameters);
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.ok) {
        if (parameters.address != undefined) {
          attendsTable.setValueFromCoords(
            servesList[0].cell.dataset.x,
            servesList[0].cell.dataset.y,
            "C"
          );
          hideModal();
          alertsToggle("Служебная записка подтверждена!", "success", 6000);
        } else {
          if (servesList.length == 1) {
            if (parameters[0].approval == 3) {
              attendsTable.setValueFromCoords(
                servesList[0].cell.dataset.x,
                servesList[0].cell.dataset.y,
                "ПРОВ"
              );
              hideModal();
              alertsToggle("Служебная записка добавлена!", "success", 6000);
            } else {
              attendsTable.setValueFromCoords(
                servesList[0].cell.dataset.x,
                servesList[0].cell.dataset.y,
                "С"
              );
              hideModal();
              alertsToggle("Служебная записка подтверждена!", "success", 6000);
            }
          } else {
            if (parameters[0].approval == 3) {
              servesList.forEach((s) => {
                attendsTable.setValueFromCoords(
                  s.cell.dataset.x,
                  s.cell.dataset.y,
                  "ПРОВ"
                );
              });
              hideModal();
              alertsToggle("Служебные записки добавлены!", "success", 6000);
            } else {
              servesList.forEach((s) => {
                attendsTable.setValueFromCoords(
                  s.cell.dataset.x,
                  s.cell.dataset.y,
                  "С"
                );
              });
              hideModal();
              alertsToggle("Служебные записки подтверждены!", "success", 6000);
            }
          }
        }
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            alertsToggle(newD, "danger", 5000);
            console.log(newD);
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

async function contextMenuServesToWatch(servesToWatch) {
  let parameters = getDataToServesRequest(servesToWatch);
  console.log(parameters);
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";
  clearInterval(rotateInterval);

  modalTitle.innerText = `Просмотр служебных записок`;

  showModalInTable();

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);

  let data = await getServes(parameters);
  console.log(data);
  if (!data) {
    hideModal();
    preLoadingImg.remove();
    return;
  }
  let servesContainer = drawServes(data, servesToWatch);
  modalBody.append(servesContainer);
}

function getDataToServesRequest(servesToWatch) {
  let parameters = [];

  servesToWatch.forEach((s) => {
    let parametersObject = {
      name_id: s.name_id,
      object_id: s.object_id,
      date: s.date,
    };
    parameters.push(parametersObject);
  });

  return parameters;
}

async function getServes(parameters) {
  let result;
  await fetch("/api/serves/get", {
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
      result = data;
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            alertsToggle(newD, "danger", 5000);
            console.log(newD);
            result = null;
          });
        });
      }
      if (response.status >= 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
        result = null;
      }
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
  return result;
}

function drawServes(data, servesToWatch) {
  let servesContainer = document.createElement("div");
  servesContainer.id = "servesContainer";
  if (data.length == 1) {
    servesContainer.classList.add("one-serve-container");
  } else if (data.length >= 3) {
    servesContainer.classList.add("many-serve-container");
  }

  data.forEach((s) => {
    let serveContainer = document.createElement("div");
    serveContainer.className = "serve-container";

    let left = document.createElement("div");
    left.className = "left-section";

    let employeeNameContainer = document.createElement("div");
    employeeNameContainer.classList.add(
      "serve-field-container",
      "left-section-first"
    );
    let employeeNameLabel = document.createElement("label");
    employeeNameLabel.innerText = "Сотрудник:";
    let employeeName = document.createElement("div");
    employeeName.innerText = s.name;

    let objectNameContainer = document.createElement("div");
    objectNameContainer.className = "serve-field-container";
    let objectNameLabel = document.createElement("label");
    objectNameLabel.innerText = "Подопечный:";
    let objectName = document.createElement("div");
    objectName.innerText = s.object;

    let middle = document.createElement("div");
    middle.className = "middle-section";

    let reasonContainer = document.createElement("div");
    reasonContainer.className = "serve-field-container";
    let reasonLabel = document.createElement("label");
    reasonLabel.innerText = "Комментарий:";
    let reason = document.createElement("div");
    reason.innerText = s.comment;

    let right = document.createElement("div");
    right.className = "right-section";

    if (!s.address) {
      null;
    } else {
      let addressContainer = document.createElement("div");
      addressContainer.classList.add("serve-field-container", "serve-address");
      let addressLabel = document.createElement("label");
      addressLabel.innerText = "Адрес:";
      let address = document.createElement("div");
      address.innerText = s.address;

      addressContainer.append(addressLabel, address);
      right.prepend(addressContainer);
    }

    let additionalFields = document.createElement("div");
    additionalFields.className = "serve-additional-fields";

    let dateContainer = document.createElement("div");
    dateContainer.className = "serve-field-container";
    let dateLabel = document.createElement("label");
    dateLabel.innerText = "Дата:";
    let date = document.createElement("div");
    date.innerText = s.date;

    let statusContainer = document.createElement("div");
    statusContainer.className = "serve-field-container";
    let statusLabel = document.createElement("label");
    statusLabel.innerText = "Статус:";
    let status = document.createElement("div");
    if (s.approval == 3) {
      status.innerText = "Проверяется";
    } else if (s.approval == 1) {
      status.innerText = "Подтверждено";
    }

    employeeNameContainer.append(employeeNameLabel, employeeName);
    objectNameContainer.append(objectNameLabel, objectName);
    reasonContainer.append(reasonLabel, reason);
    dateContainer.append(dateLabel, date);
    statusContainer.append(statusLabel, status);

    additionalFields.append(dateContainer, statusContainer);

    left.append(employeeNameContainer, objectNameContainer);
    middle.append(reasonContainer);
    right.append(additionalFields);

    serveContainer.append(left, middle, right);

    servesContainer.append(serveContainer);
  });

  clearInterval(rotateInterval);
  preLoadingImg.remove();
  return servesContainer;
}

function contextMenuServesToDelete(servesToDelete) {
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";

  modalTitle.innerText = `Удаление служебных записок`;

  let deleteMessageContainer = document.createElement("div");
  deleteMessageContainer.id = "deleteMessageContainer";

  let deleteMessage = document.createElement("div");
  deleteMessage.id = "deleteMessage";
  deleteMessage.innerText =
    "Вы действительно хотите удалить выбранные служебные записки?";

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
  saveBtn.innerText = "Подтвердить";
  saveBtn.addEventListener("click", () => {
    deleteServes(servesToDelete);
  });

  btnsContainer.append(cancelBtn, saveBtn);
  deleteMessageContainer.append(deleteMessage, btnsContainer);
  modalBody.append(deleteMessageContainer);

  showModalInTable();
}

function deleteServes(servesToDelete) {
  let parameters = [];
  servesToDelete.forEach((s) => {
    let parametersObject = {
      name_id: s.name_id,
      object_id: s.object_id,
      date: s.date,
    };
    parameters.push(parametersObject);
  });
  console.log(parameters);
  fetch("/api/serves/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.ok) {
        servesToDelete.forEach((s) => {
          attendsTable.setValueFromCoords(
            s.cell.dataset.x,
            s.cell.dataset.y,
            "Н/Б"
          );
        });
        hideModal();
        alertsToggle("Служебные записки удалены!", "success", 5000);
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            alertsToggle(newD, "danger", 5000);
            console.log(newD);
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

function contextMenuServesToApprove(servesToApprove) {
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";

  modalTitle.innerText = `Подтверждение служебных записок`;

  let approveMessageContainer = document.createElement("div");
  approveMessageContainer.id = "approveMessageContainer";

  let approveMessage = document.createElement("div");
  approveMessage.id = "approveMessage";
  approveMessage.innerText =
    "Вы действительно хотите подтвердить выбранные служебные записки?";

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
  saveBtn.innerText = "Подтвердить";
  saveBtn.addEventListener("click", () => {
    approveServes(servesToApprove);
  });

  btnsContainer.append(cancelBtn, saveBtn);
  approveMessageContainer.append(approveMessage, btnsContainer);
  modalBody.append(approveMessageContainer);

  showModalInTable();
}

function approveServes(servesToApprove) {
  let parameters = [];
  servesToApprove.forEach((s) => {
    let parametersObject = {
      name_id: s.name_id,
      object_id: s.object_id,
      date: s.date,
      approval: 1,
    };
    parameters.push(parametersObject);
  });
  console.log(parameters);

  fetch("/api/serves", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.ok) {
        servesToApprove.forEach((s) => {
          attendsTable.setValueFromCoords(
            s.cell.dataset.x,
            s.cell.dataset.y,
            "С"
          );
        });
        hideModal();
        alertsToggle("Служебные записки подтверждены!", "success", 5000);
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            alertsToggle(newD, "danger", 5000);
            console.log(newD);
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

async function contextMenuAddObject(object, x, y, e, lastRowOfEmployee) {
  console.log(object, x, y, e, lastRowOfEmployee);
  let nameId = parseInt(attendsTable.getCellFromCoords(1, y).innerText);
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";

  modalTitle.innerText = `Добавление подопечного в таблицу`;

  showModalInTable();

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);

  asyncFetchController = new AbortController();

  await getObjectsInModal();
  console.log(objectsNameList);

  let inputsContainerInModal = createObjectContentInModal(
    nameId,
    lastRowOfEmployee
  );
  modalBody.append(inputsContainerInModal);
}

async function getObjectsInModal() {
  if (!asyncFetchController) return;
  await fetch("/api/objects?active=true", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: asyncFetchController.signal,
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }

      return Promise.reject(response);
    })
    .then((data) => {
      console.log(data);
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

function createObjectContentInModal(nameId, lastRowOfEmployee) {
  let inputsContainerInModal = document.createElement("div");
  inputsContainerInModal.id = "inputsContainerInModal";

  let objectSelect = document.createElement("button");
  objectSelect.id = "objectSelect";
  objectSelect.innerHTML = `По очереди выберите подопечных из списка <span class="material-icons"> arrow_drop_down </span>`;
  objectSelect.setAttribute("input-type", "object");
  objectSelect.onclick = createObjectsListInModal;
  objectSelect.addEventListener("click", (e) => {
    currentSelect = e.target;
  });

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
  saveBtn.addEventListener("click", () => {
    insertObjectIntoTable(nameId, lastRowOfEmployee);
  });

  btnsContainer.append(cancelBtn, saveBtn);

  inputsContainerInModal.append(objectSelect, btnsContainer);
  return inputsContainerInModal;
}

function createObjectsListInModal() {
  let inputsContainerInModal = document.getElementById(
    "inputsContainerInModal"
  );
  let objectSelect = document.getElementById("objectSelect");
  objectSelect.style.display = "none";

  if (document.getElementById("objectListContainer")) {
    document.getElementById("objectListContainer").remove();
  }
  if (document.getElementById("addressContainer")) {
    document.getElementById("addressContainer").remove();
  }

  let objectListContainer = document.createElement("div");
  objectListContainer.id = "objectListContainer";

  let objectSearch = document.createElement("input");
  objectSearch.id = "objectSearch";
  objectSearch.type = "text";
  objectSearch.oninput = nameSearchInModal;

  let objectList = document.createElement("div");
  objectList.id = "objectList";

  renderListOfNamesInModal(objectsNameList, objectList);

  let btnsContainer = document.getElementById("btnsContainer");
  let saveBtn = document.getElementById("saveBtn");

  let backBtn = document.createElement("button");
  backBtn.id = "backBtn";
  backBtn.innerText = "Назад";
  backBtn.onclick = returnBackInModal;

  btnsContainer.insertBefore(backBtn, saveBtn);
  objectListContainer.append(objectSearch, objectList);
  inputsContainerInModal.prepend(objectListContainer);

  objectSearch.focus();
}

function nameSearchInModal() {
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
  renderListOfNamesInModal(resultList, container);
}

function renderListOfNamesInModal(list, container) {
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
    div.setAttribute("address", r.address);
    div.onclick = chosenNameInModal;

    div.append(anc);
    container.append(div);
  });
  container.style.display = "block";
}

function chosenNameInModal(e) {
  let input = null;
  let select = null;
  let element = e.currentTarget;
  console.log(element);
  let name = element.getAttribute("name");
  let address = element.getAttribute("address");
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
  returnBackInModal();
  select.innerText = name;

  let addressContainer = document.createElement("div");
  addressContainer.id = "addressContainer";
  addressContainer.innerText = `Адрес: ${address}`;
  addressContainer.setAttribute("object_id", element.getAttribute("object_id"));

  let inputsContainerInModal = document.getElementById(
    "inputsContainerInModal"
  );
  let btnsContainer = document.getElementById("btnsContainer");
  inputsContainerInModal.insertBefore(addressContainer, btnsContainer);
}

function returnBackInModal() {
  currentSelect = null;
  let objectSelect = document.getElementById("objectSelect");
  objectSelect.style.display = "flex";

  let objectListContainer = document.getElementById("objectListContainer");
  objectListContainer ? (objectListContainer.innerHTML = "") : null;

  let backBtn = document.getElementById("backBtn");
  backBtn.remove();
}

function insertObjectIntoTable(nameId, lastRowOfEmployee) {
  let objectSelect = document.getElementById("objectSelect");
  let addressContainer = document.getElementById("addressContainer");

  let objectName = objectSelect.innerText;
  let objectId = addressContainer.getAttribute("object_id");

  attendsTable.insertRow(
    [, nameId, "", objectName, objectId],
    lastRowOfEmployee,
    0
  );
  reMergeCells();
  hideModal();
}

async function contextMenuCreateObjectForm(object, x, y, e) {
  let objectId = attendsTable.getCellFromCoords(
    objectIdColumnIndex,
    y
  ).innerText;
  let modalBody = document.getElementById("modalBody");
  let modalTitle = document.getElementById("modalTitle");
  modalBody.innerHTML = "";

  modalTitle.innerText = `Просмотр данных о подопечном`;

  showModalInTable();

  let preLoadingImg = document.createElement("img");
  preLoadingImg.src = "../static/icons/loading.png";
  preLoadingImg.id = "preLoadingImg";
  modalBody.prepend(preLoadingImg);

  rotateInterval = setInterval(rotateImg, 50);

  asyncFetchController = new AbortController();

  let data = await getOneObject(objectId);
  let objectContent = createForm();
  modalBody.append(objectContent);
  fillFormWithData(data);
}

async function getOneObject(objectId) {
  if (!asyncFetchController) return;
  let result;
  await fetch(`/api/objects/${objectId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal: asyncFetchController.signal,
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }
      return Promise.reject(response);
    })
    .then((data) => {
      result = data;

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
            result = null;
          });
        });
      }
      if (response.status >= 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
        result = null;
      }
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
  return result;
}

function createForm() {
  if (document.getElementById("objectContent")) {
    document.getElementById("objectContent").remove();
  }
  let objectContent = document.createElement("div");
  objectContent.id = "objectContent";

  let allFieldsContainer = document.createElement("div");
  allFieldsContainer.id = "allFieldsContainer";

  let nameFieldContainer = document.createElement("div");
  nameFieldContainer.id = "nameFieldContainer";

  let nameFieldLabel = document.createElement("label");
  nameFieldLabel.htmlFor = "nameField";
  nameFieldLabel.innerText = "ФИО подопечного: ";

  let nameField = document.createElement("input");
  nameField.id = "nameField";
  nameField.type = "text";
  nameField.readOnly = true;

  let divisionFieldContainer = document.createElement("div");
  divisionFieldContainer.id = "divisionFieldContainer";

  let divisionFieldLabel = document.createElement("label");
  divisionFieldLabel.htmlFor = "divisionField";
  divisionFieldLabel.innerText = "Подразделение:";

  let divisionField = document.createElement("select");
  divisionField.id = "divisionField";
  divisionField.disabled = true;

  let options = JSON.parse(localStorage.getItem("access"));
  options.forEach((d) => {
    const divisionName = d.division;
    let option = document.createElement("option");
    option.setAttribute("division_id", d.division_id);
    option.innerText = divisionName;
    divisionField.appendChild(option);
  });

  let restFields = document.createElement("div");
  restFields.id = "restFields";

  let activeField = document.createElement("div");
  activeField.id = "activeField";

  let activeCheck = document.createElement("input");
  activeCheck.id = "activeCheck";
  activeCheck.type = "checkbox";
  activeCheck.checked = "true";
  activeCheck.disabled = true;

  let activeCheckLabel = document.createElement("label");
  activeCheckLabel.htmlFor = "activeCheck";
  activeCheckLabel.innerText = "Показывать в списке для заполнения шахматки";

  let noPaymentField = document.createElement("div");
  noPaymentField.id = "noPaymentField";

  let noPaymentCheck = document.createElement("input");
  noPaymentCheck.id = "noPaymentCheck";
  noPaymentCheck.type = "checkbox";
  noPaymentCheck.disabled = true;

  let noPaymentCheckLabel = document.createElement("label");
  noPaymentCheckLabel.htmlFor = "noPaymentCheck";
  noPaymentCheckLabel.innerText = "Частично платная основа, но не доплачивает";

  let dateFieldsContainer = document.createElement("div");
  dateFieldsContainer.id = "dateFieldsContainer";

  let startDateContainer = document.createElement("div");
  startDateContainer.id = "startDateContainer";

  let startDateLabel = document.createElement("label");
  startDateLabel.id = "startDateLabel";
  startDateLabel.innerText = "Дата приема на обслуж.";
  startDateLabel.htmlFor = "startDateField";

  let startDateField = document.createElement("input");
  startDateField.id = "startDateField";
  startDateField.type = "date";
  startDateField.readOnly = true;

  let endDateContainer = document.createElement("div");
  endDateContainer.id = "endDateContainer";

  let endDateLabel = document.createElement("label");
  endDateLabel.id = "endDateLabel";
  endDateLabel.innerText = "Дата снятия с обслуж.";
  endDateLabel.htmlFor = "endDateField";

  let endDateField = document.createElement("input");
  endDateField.id = "endDateField";
  endDateField.type = "date";
  endDateField.readOnly = true;

  let phoneFieldContainer = document.createElement("div");
  phoneFieldContainer.id = "phoneFieldContainer";

  let phoneFieldLabel = document.createElement("label");
  phoneFieldLabel.htmlFor = "phoneField";
  phoneFieldLabel.innerText = "Контактные данные: ";

  let phoneField = document.createElement("textarea");
  phoneField.id = "phoneField";
  phoneField.cols = "49";
  phoneField.rows = "3";
  phoneField.readOnly = true;

  let addressFieldContainer = document.createElement("div");
  addressFieldContainer.id = "addressFieldContainer";

  let switchAddressContainer = document.createElement("div");
  switchAddressContainer.id = "switchAddressContainer";

  let switchAddressLabelName = document.createElement("label");
  switchAddressLabelName.id = "switchAddressLabelName";
  switchAddressLabelName.innerText = "Изменить источник адресов: ";

  let switchAddressLabel = document.createElement("label");
  switchAddressLabel.id = "switchAddressLabel";

  let switchAddressBtn = document.createElement("input");
  switchAddressBtn.id = "switchAddressBtn";
  switchAddressBtn.type = "checkbox";
  if (localStorage.getItem("address-sorce") === "1") {
    switchAddressBtn.checked = false;
  } else if (localStorage.getItem("address-sorce") === "2") {
    switchAddressBtn.checked = true;
  } else {
    switchAddressBtn.checked = true;
  }

  let switchAddressSpan = document.createElement("span");
  switchAddressSpan.id = "switchAddressSpan";
  switchAddressSpan.onclick = switchAddress;

  let addressFieldLabel = document.createElement("label");
  addressFieldLabel.id = "addressFieldLabel";
  addressFieldLabel.innerText = "Адрес подопечного: ";

  let addressField = document.createElement("input");
  addressField.id = "addressField";
  addressField.type = "text";
  addressField.setAttribute("list", "addressSelect");
  addressField.placeholder = "Начните вводить адрес";
  addressField.readOnly = true;

  let apartmentFieldContainer = document.createElement("div");
  apartmentFieldContainer.id = "apartmentFieldContainer";

  let apartmentFieldLabel = document.createElement("label");
  apartmentFieldLabel.id = "apartmentFieldLabel";
  apartmentFieldLabel.innerText = "Номер квартиры, подъезд, код домофона и т.д";
  apartmentFieldLabel.htmlFor = "apartmentField";

  let apartmentField = document.createElement("input");
  apartmentField.id = "apartmentField";
  apartmentField.type = "text";
  apartmentField.readOnly = true;

  let personalServiceFieldContainer = document.createElement("div");
  personalServiceFieldContainer.id = "personalServiceFieldContainer";

  let personalServiceFieldLabel = document.createElement("label");
  personalServiceFieldLabel.id = "personalServiceFieldLabel";
  personalServiceFieldLabel.innerText = "ИППСУ после пересмотра:";
  personalServiceFieldLabel.htmlFor = "personalServiceField";

  let personalServiceField = document.createElement("input");
  personalServiceField.id = "personalServiceField";
  personalServiceField.type = "text";
  personalServiceField.maxLength = 70;
  personalServiceField.readOnly = true;

  let btnsContainer = document.createElement("div");
  btnsContainer.id = "btnsContainer";

  let cancelBtn = document.createElement("button");
  cancelBtn.id = "cancelBtn";
  cancelBtn.type = "button";
  cancelBtn.innerText = "Закрыть";
  cancelBtn.onclick = hideModal;

  nameFieldContainer.append(nameFieldLabel, nameField);
  switchAddressLabel.append(switchAddressBtn, switchAddressSpan);
  switchAddressContainer.append(switchAddressLabelName, switchAddressLabel);
  startDateContainer.append(startDateLabel, startDateField);
  endDateContainer.append(endDateLabel, endDateField);
  phoneFieldContainer.append(phoneFieldLabel, phoneField);
  addressFieldContainer.append(
    addressFieldLabel,
    addressField,
    switchAddressContainer
  );
  apartmentFieldContainer.append(apartmentFieldLabel, apartmentField);
  personalServiceFieldContainer.append(
    personalServiceFieldLabel,
    personalServiceField
  );

  divisionFieldContainer.append(divisionFieldLabel, divisionField);
  restFields.append(activeField, noPaymentField);
  activeField.append(activeCheck, activeCheckLabel);
  noPaymentField.append(noPaymentCheck, noPaymentCheckLabel);
  dateFieldsContainer.append(startDateContainer, endDateContainer);
  btnsContainer.append(cancelBtn);

  allFieldsContainer.append(
    nameFieldContainer,
    divisionFieldContainer,
    restFields,
    dateFieldsContainer,
    phoneFieldContainer,
    addressFieldContainer,
    apartmentFieldContainer,
    personalServiceFieldContainer
  );

  objectContent.append(allFieldsContainer, btnsContainer);

  return objectContent;
}

function fillFormWithData(data) {
  let name = document.getElementById("nameField");
  name.setAttribute("object-id", data.object_id);
  let options = document.getElementById("divisionField").childNodes;
  let noPayments = document.getElementById("noPaymentCheck");
  let active = document.getElementById("activeCheck");
  let phone = document.getElementById("phoneField");
  let address = document.getElementById("addressField");
  let startDate = document.getElementById("startDateField");
  let endDate = document.getElementById("endDateField");
  let apartment = document.getElementById("apartmentField");
  let personalService = document.getElementById("personalServiceField");

  name.value = data.name;
  options.forEach((o) =>
    data.division_name === o.innerText ? (o.selected = true) : null
  );
  data.no_payments ? (noPayments.checked = true) : null;
  data.active ? (active.checked = true) : null;
  phone.value = data.phone;
  address.value = data.address;
  address.setAttribute("lat", data.latitude);
  address.setAttribute("lon", data.longitude);
  address.addEventListener("input", () => {
    addressContainer.innerHTML = "";
    modalForm.append(addressOuterContainer);
    addressType();
  });
  startDate.value = data.admission_date;
  endDate.value = data.denial_date;
  apartment.value = data.apartment_number;
  personalService.value = data.personal_service_after_revision;
}
