import { alertsToggle } from "../../../v1/alerts.js";
import { hideModal } from "../../../v1/modal.js";
import { dictionary } from "../../../v1/translation_dict.js";
import { checkPattern } from "../../../v1/check_pattern.js";

let analysisTable;
let currentRowOfTable;

// let requestTableBtn = document.getElementById("requestBtn");
// requestTableBtn.onclick = requestTable;

let startDate = document.getElementById("startDateOfPeriod");
let endDate = document.getElementById("endDateOfPeriod");

// window.onload = function (e) {
//   week(e);
// };

// function week(e) {
//   e.preventDefault();

//   startDate.classList.remove("date-highlight", "fade-out-box");
//   endDate.classList.remove("date-highlight", "fade-out-box");

//   startDate.value = "";
//   endDate.value = "";

//   let date = new Date();
//   let day = date.getDate();
//   let month = date.getMonth();
//   let year = date.getFullYear();
//   let firstDate = new Date(year, month, day - 7, 12)
//     .toISOString()
//     .split("T")[0];
//   let lastDate = new Date(year, month, day, 12).toISOString().split("T")[0];

//   startDate.value = firstDate;
//   endDate.value = lastDate;

//   startDate.classList.add("date-highlight");
//   endDate.classList.add("date-highlight");
//   setTimeout(() => {
//     startDate.classList.add("fade-out-box");
//     endDate.classList.add("fade-out-box");
//     setTimeout(() => {
//       startDate.classList.remove("date-highlight", "fade-out-box");
//       endDate.classList.remove("date-highlight", "fade-out-box");
//     }, 600);
//   }, 600);
// }

// function getTableParameters(e) {
//   e.preventDefault();
//   let startDate = document.getElementById("startDateOfPeriod").value;
//   let endDate = document.getElementById("endDateOfPeriod").value;

//   $("#preLoadContainer")[0].style.display = "flex";

//   if (startDate == "" || endDate == "") {
//     $("#preLoadContainer")[0].style.display = "none";
//     document.getElementById("requestBtn").disabled = false;
//     alertsToggle("Укажите дату!", "warning", 5000);
//     return;
//   }
//   let parameters = {
//     date_from: startDate,
//     date_to: endDate,
//   };

//   console.log(parameters);
//   return parameters;
// }

window.onload = function (e) {
  getTable(e);
};

// function requestTable(e) {
//   document.getElementById("requestBtn").disabled = true;
//   let parameters = getTableParameters(e);
//   if (parameters == undefined) return;
//   getTable(parameters);
// }

function getTable(s) {
  $.ajax({
    url: "/api/analysis/table",
    method: "GET",
    contentType: "application/json",
  })
    .done(function (data) {
      console.log(data);
      analysisTable = new DataTable("#analysisTable", {
        aaData: data,
        scrollX: "100%",
        scrollY: "70vh",
        scrollCollapse: true,
        paging: false,
        language: {
          search: "Поиск: ",
          info: "Найдено по запросу: _TOTAL_ ",
          infoFiltered: "( из _MAX_ записей )",
          infoEmpty: "",
          zeroRecords: "Совпадений не найдено",
        },
        dom: "<'pre-table-row'<'new-emp-container'B>f>rtip",

        columns: [
          { data: "division" },
          { data: "name" },
          { data: "name_id" },
          { data: "datetime" },
          {
            data: "problem",
            render: function (data) {
              return data ? "Возможно" : "Нет";
            },
          },
          { data: "since_last_location" },
          {
            data: "works_today",
            render: function (data) {
              return data ? "Да" : "Нет";
            },
          },
          { data: "phone" },
        ],
        initComplete: function () {
          this.api()
            .columns()
            .every(function () {
              let column = this;
              let title = column.footer().textContent;

              // Create input element
              let input = document.createElement("input");
              input.placeholder = title;
              column.footer().replaceChildren(input);

              // Event listener for user input
              input.addEventListener("keyup", () => {
                if (column.search() !== this.value) {
                  column.search(input.value).draw();
                }
              });
            });
        },
      });

      $("#preLoadContainer")[0].style.display = "none";
      $("#tableContainer")[0].style.opacity = 1;
      $("#analysisTable").DataTable().draw();
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
      if (xhr.status == 403) {
        $("#preLoadContainer")[0].style.display = "none";
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
}
