import { alertsToggle } from "../../alerts.js";
import { dictionary } from "../../translation_dict.js";

let attendsTable;
let currentRowOfTable;

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
  frequency: { title: "Кол-во", name: "frequency", width: 53 },
};

jspreadsheet.createTable = () => {};

function getTable(parameters) {
  let table = document.getElementById("attendsTable");
  table ? (table.innerHTML = "") : null;
  $.ajax({
    url: "/api/report",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(parameters),
  }).done(function (data) {
    console.log("data: ", data);
    let columns = data.horizontal_report.columns;
    let newColumns = [];
    columns.forEach((column) => {
      let newColumn = formatDict[column]
        ? formatDict[column]
        : { title: column, name: column, width: 70 };
      newColumns.push(newColumn);
    });
    console.log("newColumns: ", newColumns);
    console.log("Row data: ", data.horizontal_report.data);
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
  toggleCommentsBtn.innerHTML = `<span class="material-icons">speaker_notes</span>`;
  toggleCommentsBtn.title = "Скрыть столбец с комментариями";
  toggleCommentsBtn.onclick = toggleComments;

  let duplicatesBtn = document.createElement("button");
  duplicatesBtn.id = "duplicatesBtn";
  duplicatesBtn.innerHTML = `<span class="material-icons">people</span>`;
  duplicatesBtn.title = "Показать дубликаты";
  duplicatesBtn.onclick = showDuplicates;

  let refreshTableBtn = document.createElement("button");
  refreshTableBtn.id = "refreshTableBtn";
  refreshTableBtn.innerHTML = `<span class="material-icons">refresh</span>`;
  refreshTableBtn.title = "Обновить данные в отчете";
  refreshTableBtn.onclick = updateDataInTable;

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

  let table = document.getElementsByClassName("jexcel_content")[0].children[0];
  table.style.border = "none";
}

function noneOutlineBorder() {
  this.style.border = "1px solid gray";
  this.style.outline = "none";
}

function addEmployeeInTable() {
  console.log("addEmployeeInTable");
}

function downloadXlsx() {
  console.log("downloadXlsx");
}

function toggleComments() {
  console.log("toggleComments");
}

function showDuplicates() {
  console.log("showDuplicates");
}

function updateTable(e) {
  let parameters = getTableParameters(e);
  updateDataInTable(parameters);
}

function updateDataInTable(parameters) {
  let table = attendsTable;
  let selectedCells = table.selectedCell;
  let search = document.getElementsByClassName("jexcel_search")[0];
  let searchValue = search.value;

  $.ajax({
    url: "/api/report",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(parameters),
  }).done(function (data) {
    console.log("data: ", data);
    let columns = data.horizontal_report.columns;
    let newColumns = [];
    columns.forEach((column) => {
      let newColumn = formatDict[column]
        ? formatDict[column]
        : { title: column, name: column, width: 70 };
      newColumns.push(newColumn);
    });
  });

  console.log("updateDataInTable");
}

// function getTable(parameters) {
//   $.ajax({
//     url: "/api/report",
//     method: "POST",
//     contentType: "application/json",
//     data: JSON.stringify(parameters),
//   }).done(function (data) {
//     console.log(data);

//     let columns = data.horizontal_report.columns;
//     let numColumns = columns.length;
//     let columnInit = [];
//     let table = document.getElementById("attendsTable").children[0].children[0];

//     for (let i = 0; i < numColumns; i++) {
//       columnInit.push({ title: columns[i] });
//       // let th = document.createElement("th");
//       // th.innerText = columns[i];
//       // table.appendChild(th);
//     }
//     console.log(columnInit);

//     let windowHeight = window.innerHeight - 220;
//     attendsTable = new DataTable("#attendsTable", {
//       aaData: data,
//       scrollY: windowHeight,
//       scrollX: "100%",
//       scrollCollapse: false,
//       paging: false,
//       language: {
//         search: "Поиск: ",
//         info: "Найдено по запросу: _TOTAL_ ",
//         infoFiltered: "( из _MAX_ записей )",
//         infoEmpty: "",
//         zeroRecords: "Совпадений не найдено",
//       },
//       dom: "<'pre-table-row'<'btns-container'B>f>rtip",
//       buttons: [
//         {
//           text: "Сотрудник +",
//           className: "add-emp-btn",
//           attr: {
//             id: "addEmployee",
//           },
//           action: function () {
//             console.log("employee");
//           },
//         },
//         {
//           text: "Скачать",
//           className: "download-btn",
//           attr: {
//             id: "downloadBtn",
//           },
//           action: function () {
//             console.log("download");
//           },
//         },
//         {
//           text: "Комментарии",
//           className: "comment-toggle-btn",
//           attr: {
//             id: "commentToggleBtn",
//           },
//           action: function () {
//             console.log("comment");
//           },
//         },
//         {
//           text: "Дубликаты",
//           className: "duplicates-btn",
//           attr: {
//             id: "duplicatesBtn",
//           },
//           action: function () {
//             console.log("duplicates");
//           },
//         },
//         {
//           text: "Обновить",
//           className: "refresh-btn",
//           attr: {
//             id: "refreshBtn",
//           },
//           action: function () {
//             console.log("refresh");
//           },
//         },
//       ],

//       columns: columnInit,
//     });

//     $("#preLoadContainer")[0].style.display = "none";
//     $("#tableParametersContainer")[0].style.display = "flex";
//     $("#tableContainer")[0].style.opacity = 1;
//     $("#objectTable").DataTable().draw();
//   });
// }
