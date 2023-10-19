import { alertsToggle } from "../../alerts.js";
import { hideModal } from "../../modal.js";
import { dictionary } from "../../translation_dict.js";

let attendsTable;
let currentRowOfTable;

const closeModal = document.getElementById("closeModal");
closeModal.addEventListener("click", hideModal);

let divisionField = document.getElementById("divisionSelect");
let access = JSON.parse(localStorage.getItem("access"));
access.forEach((d) => {
  const divisionName = d.division;
  let option = document.createElement("option");
  option.setAttribute("division_id", d.division_id);
  option.innerText = divisionName;
  divisionField.append(option);
});

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

function previousMonthF(e) {
  e.preventDefault();
  startDate.value = "";
  endDate.value = "";

  let date = new Date();
  let month = date.getMonth();
  let year = date.getFullYear();
  let firstDate = new Date(year, month - 1, 1, 12).toISOString().split("T")[0];
  let lastDate = new Date(year, month + 1, 0, 12).toISOString().split("T")[0];

  startDate.value = firstDate;
  endDate.value = lastDate;
}

function currentMonthF(e) {
  e.preventDefault();
  startDate.value = "";
  endDate.value = "";

  let date = new Date();
  let month = date.getMonth();
  let year = date.getFullYear();
  let firstDate = new Date(year, month, 1, 12).toISOString().split("T")[0];
  let lastDate = new Date(year, month + 1, 0, 12).toISOString().split("T")[0];

  startDate.value = firstDate;
  endDate.value = lastDate;
}

let requesTableBtn = document.getElementById("requestBtn");
requesTableBtn.onclick = requestTable;

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
  let counts = countsR == "1" ? false : true;

  if (startDate == "" || endDate == "") {
    $("#preLoadContainer")[0].style.display = "none";
    alertsToggle("Укажите дату!", "warning", 5000);
    return;
  }
  let parameters = {
    division: divisionId,
    date_from: startDate,
    date_to: endDate,
    counts: counts,
  };

  console.log(parameters);
  return parameters;
}

function requestTable(e) {
  let parameters = getTableParameters(e);
  if (parameters == undefined) return;
  getTable(parameters);
}

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
};

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
      if (localStorage.getItem("toggleComments") === "hide") {
        attendsTable.hideColumn(2);
      }
    })
    .fail(function (xhr, status, error) {
      let json = xhr.responseJSON;
      if (json.status == 422) {
        $("#preLoadContainer")[0].style.display = "none";
        alertsToggle(json.detail, "danger", 6000);
      }
    });
}

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

function noneOutlineBorder() {
  this.style.border = "1px solid gray";
  this.style.outline = "none";
}

let employeesNameList = [];
let objectsNameList = [];
let rotateInterval;

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
function rotateImg() {
  angle += 10;
  let img = document.getElementById("preLoadingImg");
  img.style.transform = `rotateZ(${angle}deg)`;
}

async function getEmployees() {
  await fetch("/api/employees", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      employeesNameList = data;
      console.log("employeesNameList ", employeesNameList);
    });
}

async function getObjects() {
  await fetch("/api/objects?active=true", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      objectsNameList = data;

      console.log("objectsNameList", objectsNameList);

      clearInterval(rotateInterval);
      let img = document.getElementById("preLoadingImg");
      img.remove();
    });
}

var currentSelect;
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

function createEmployeesList() {
  console.log("Employees list", employeesNameList);
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

function createObjectsList() {
  console.log("Objects list", objectsNameList);
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
  console.log("createObjectsList");

  objectSearch.focus();
}

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

function renderListOfNames(list, container) {
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
}

function chosenName(e) {
  let input = null;
  let select = null;
  let element = e.target;
  let name = element.getAttribute("name");
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

  console.log(name);
  console.log(input);
}

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

  // attendsTable.destroyMerged();

  [...elementsToAdd].slice(1).forEach((e) => {
    let objectName = e.getAttribute("name");
    let objectId = e.getAttribute("object_id");
    console.log(employeeName, objectName);
    attendsTable.insertRow(
      [employeeName, employeeId, "", objectName, objectId],
      0,
      1
    );
  });

  hideModal();

  reMergeCells();
}

function downloadXlsx(e) {
  let parameters = getTableParameters(e);
  $("#preLoadContainer")[0].style.display = "none";
  getXlsx(parameters);
}

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

function toggleComments() {
  let toggleCommentsBtn = document.getElementById("toggleCommentsBtn");
  if (
    localStorage.getItem("toggleComments") == "show" ||
    localStorage.getItem("toggleComments") == null
  ) {
    toggleCommentsBtn.innerHTML = `<span class="material-icons">speaker_notes</span>`;
    attendsTable.hideColumn(2);
    localStorage.setItem("toggleComments", "hide");
  } else if (localStorage.getItem("toggleComments") == "hide") {
    toggleCommentsBtn.innerHTML = `<span class="material-icons">speaker_notes_off</span>`;
    attendsTable.showColumn(2);
    localStorage.setItem("toggleComments", "show");
  }

  console.log("toggleComments");
}

function showDuplicates() {
  console.log("showDuplicates");
}

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
  console.log("Прошли selectedCells");
  let search = document.getElementsByClassName("jexcel_search")[0];
  if (search.value != null || search.value != undefined) {
    let searchValue = search.value;
    arrayOfParameters.push(searchValue);
  }
  updateDataInTable(...arrayOfParameters);
}

function updateDataInTable(parameters, table, selectedCells, searchValue) {
  $.ajax({
    url: "/api/report",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(parameters),
  }).done(function (data) {
    console.log("data: ", data);
    console.log(table);
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
  });

  console.log("updateDataInTable");
}

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
