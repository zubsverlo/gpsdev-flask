// import { alertsToggle } from "../../alerts";
// import { dictionary } from "../../translation_dict";

let usersTable;
let currentRowOfTable;

$.ajax({
  url: "/api/users",
  method: "GET",
  contentType: "application/json",
}).done(function (data) {
  console.log(data);
  let access = data.access;
  let windowHeight = window.innerHeight - 220;
  usersTable = new DataTable("#usersTable", {
    aaData: data,
    scrollY: windowHeight,
    scrollX: "100%",
    scrollCollapse: true,
    paging: false,
    language: {
      search: "Поиск: ",
      info: "Найдено по запросу: _TOTAL_ ",
      infoFiltered: "( из _MAX_ записей )",
      infoEmpty: "",
      zeroRecords: "Совпадений не найдено",
    },
    dom: "<'pre-table-row'<'new-obj-container'B>f>rtip",
    buttons: [
      {
        //add new-user button
        text: "Новый пользователь",
        className: "new-user-btn",
        attr: {
          id: "addNewUser",
        },
        action: function () {
          console.log("uahahahaha");
        },
      },
    ],

    columns: [
      { data: "id" },
      { data: "name" },
      { data: "phone" },
      { data: "phone" },
      {
        //add column with change buttons to all rows in table
        data: null,
        defaultContent: "<button class='change-btn'>Изменить</button>",
        targets: -1,
      },
    ],
  });

  $("#preLoadContainer")[0].style.display = "none";
  $("#tableContainer")[0].style.opacity = 1;
});
