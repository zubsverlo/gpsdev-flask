import { alertsToggle } from "../../../v1/alerts.js";
import { hideModal } from "../../../v1/modal.js";
import { dictionary } from "../../../v1/translation_dict.js";

let toConnectTable;
let delFromMtsTable;
let abandonedTable;
let noStatementsTable;
let mtsOnlyTable;

let currentRowOfTable;
let greetingTextBoolean = false;

$.ajax({
  url: "/api/dashboard",
  method: "GET",
  contentType: "application/json",
})
  .done(function (data) {
    console.log("response data: ", data);
    toConnectTable = new DataTable("#toConnectTable", {
      aaData: data.to_connect,
      scrollY: "70vh",
      scrollX: "100%",
      order: [[0, "desc"]],
      scrollResize: true,
      scrollCollapse: true,
      paging: false,
      language: {
        search: "Поиск: ",
        info: "Найдено по запросу: _TOTAL_ ",
        infoFiltered: "( из _MAX_ записей )",
        infoEmpty: "",
        zeroRecords: "Совпадений не найдено",
      },
      dom: "<'pre-table-row'<'greeting-text-container'B>f>rtip",
      buttons: [
        {
          text: "Текст приветствия",
          className: "greeting-text-btn",
          attr: {
            id: "greetingTextBtn",
          },
          action: function () {
            console.log("work");

            let text = `Здравствуйте, я Илья! Вы устроились к нам социальным работником. Я должен подключить вас к отслеживанию. 
Установите, пожалуйста, приложение:
https://play.google.com/store/apps/details?id=ru.mts.android.apps.coordinator
  
Потом отпишитесь, я вас зарегистрирую.`;

            if (greetingTextBoolean) {
              document.getElementById("greetingTextContainer").remove();
              greetingTextBoolean = false;
            } else {
              let greetingTextContainer = document.createElement("div");
              greetingTextContainer.id = "greetingTextContainer";

              let greetingText = document.createElement("textarea");
              greetingText.id = "greetingText";
              greetingText.rows = 10;
              greetingText.cols = 50;
              greetingText.value = text;

              greetingTextContainer.append(greetingText);
              document
                .getElementById("allTablesContainer")
                .prepend(greetingTextContainer);
              greetingText.focus();
              greetingText.select();
              greetingText.setSelectionRange(0, 99999);
              greetingTextBoolean = true;
            }
          },
        },
      ],
      columns: [
        { data: "name_id" },
        { data: "phone" },
        { data: "name" },
        { data: "division_name" },
        { data: "hire_date" },
        { data: "last_stmt_date" },
        {
          // add column with Уволить buttons to all rows in table
          data: null,
          defaultContent: "<button class='delete-btn'>Уволить</button>",
          targets: -1,
        },
        {
          // add column with WhatsApp buttons to all rows in table
          data: null,
          defaultContent: "<button class='change-btn'>WhatsApp</button>",
          targets: -2,
        },
        {
          // add column with OwnTracks buttons to all rows in table
          data: null,
          defaultContent: "<button class='owntracks-btn'>OwnTracks</button>",
          targets: -3,
        },
      ],
    });
    delFromMtsTable = new DataTable("#delFromMtsTable", {
      aaData: data.del_from_mts,
      scrollY: "70vh",
      scrollX: "100%",
      scrollResize: true,
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
      columns: [
        { data: "name_id" },
        { data: "name" },
        { data: "division_name" },
        { data: "hire_date" },
        { data: "quit_date" },
        { data: "company" },
        { data: "last_stmt_date" },
        { data: "subscriberID" },
        {
          // add column with change buttons to all rows in table
          data: null,
          defaultContent: "<button class='change-btn'>Удалить</button>",
          targets: -1,
        },
      ],
    });
    abandonedTable = new DataTable("#abandonedTable", {
      aaData: data.abandoned,
      scrollY: "70vh",
      scrollX: "100%",
      scrollResize: true,
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
      columns: [
        { data: "name_id" },
        { data: "name" },
        { data: "division_name" },
        { data: "hire_date" },
        { data: "last_stmt_date" },
        { data: "mts_active" },
        {
          // add column with change buttons to all rows in table
          data: null,
          defaultContent: "<button class='change-btn'>Уволить</button>",
          targets: -1,
        },
      ],
    });
    noStatementsTable = new DataTable("#noStatementsTable", {
      aaData: data.no_statements,
      scrollY: "70vh",
      scrollX: "100%",
      scrollResize: true,
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
      columns: [
        { data: "name_id" },
        { data: "name" },
        { data: "division_name" },
        { data: "hire_date" },
        { data: "period_init" },
        {
          // add column with change buttons to all rows in table
          data: null,
          defaultContent: "<button class='change-btn'>Удалить</button>",
          targets: -1,
        },
      ],
    });
    mtsOnlyTable = new DataTable("#mtsOnlyTable", {
      aaData: data.mts_only,
      scrollY: "70vh",
      scrollX: "100%",
      scrollResize: true,
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
      columns: [
        { data: "name" },
        { data: "company" },
        { data: "subscriberID" },
        {
          // add column with change buttons to all rows in table
          data: null,
          defaultContent: "<button class='change-btn'>Удалить</button>",
          targets: -1,
        },
      ],
    });

    $("#preLoadContainer")[0].style.display = "none";

    let toConnectTableContainer = document.getElementById(
      "toConnectTableContainer"
    );
    let toConnectTableBtn = document.getElementById("toConnectTableBtn");
    toConnectTableBtn.innerHTML = `Сотрудники на подключение (${data.to_connect.length}) <span class="material-symbols-outlined">arrow_drop_down</span>`;
    toConnectTableBtn.onclick = toggleToConnectTable;
    if (localStorage.getItem("toggle-to-connect-table") == "false") {
      toConnectTableContainer.style.display = "none";
    } else {
      toConnectTableContainer.style.display = "block";
      localStorage.setItem("toggle-to-connect-table", "true");
    }

    let delFromMtsTableContainer = document.getElementById(
      "delFromMtsTableContainer"
    );
    let delFromMtsTableBtn = document.getElementById("delFromMtsTableBtn");
    delFromMtsTableBtn.innerHTML = `Удалить из МТС (${data.del_from_mts.length}) <span class="material-symbols-outlined">arrow_drop_down</span>`;
    delFromMtsTableBtn.onclick = toggleDelFromMtsTable;
    if (localStorage.getItem("toggle-del-from-mts-table") == "false") {
      delFromMtsTableContainer.style.display = "none";
    } else {
      delFromMtsTableContainer.style.display = "block";
      localStorage.setItem("toggle-del-from-mts-table", "true");
    }

    let abandonedTableContainer = document.getElementById(
      "abandonedTableContainer"
    );
    let abandonedTableBtn = document.getElementById("abandonedTableBtn");
    abandonedTableBtn.innerHTML = `Заброшенные (${data.abandoned.length}) <span class="material-symbols-outlined">arrow_drop_down</span>`;
    abandonedTableBtn.onclick = toggleAbandonedTable;
    if (localStorage.getItem("toggle-abandoned-table") == "false") {
      abandonedTableContainer.style.display = "none";
    } else {
      abandonedTableContainer.style.display = "block";
      localStorage.setItem("toggle-abandoned-table", "true");
    }

    let noStatementsTableContainer = document.getElementById(
      "noStatementsTableContainer"
    );
    let noStatementsTableBtn = document.getElementById("noStatementsTableBtn");
    noStatementsTableBtn.innerHTML = `Без заполненных выходов (${data.no_statements.length}) <span class="material-symbols-outlined">arrow_drop_down</span>`;
    noStatementsTableBtn.onclick = toggleNoStatementsTable;
    if (localStorage.getItem("toggle-no-statements-table") == "false") {
      noStatementsTableContainer.style.display = "none";
    } else {
      noStatementsTableContainer.style.display = "block";
      localStorage.setItem("toggle-no-statements-table", "true");
    }

    let mtsOnlyTableContainer = document.getElementById(
      "mtsOnlyTableContainer"
    );
    let mtsOnlyTableBtn = document.getElementById("mtsOnlyTableBtn");
    mtsOnlyTableBtn.innerHTML = `Есть только в МТС (${data.mts_only.length}) <span class="material-symbols-outlined">arrow_drop_down</span>`;
    mtsOnlyTableBtn.onclick = toggleMtsOnlyTable;
    if (localStorage.getItem("toggle-mts-only-table") == "false") {
      mtsOnlyTableContainer.style.display = "none";
    } else {
      mtsOnlyTableContainer.style.display = "block";
      localStorage.setItem("toggle-mts-only-table", "true");
    }

    $("#allTablesContainer")[0].style.opacity = 1;

    $("#toConnectTable").DataTable().draw();
    $("#delFromMtsTable").DataTable().draw();
    $("#abandonedTable").DataTable().draw();
    $("#noStatementsTable").DataTable().draw();
    $("#mtsOnlyTable").DataTable().draw();
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

function toggleToConnectTable() {
  console.log("to connect");
  let toConnectTableContainer = document.getElementById(
    "toConnectTableContainer"
  );

  if (localStorage.getItem("toggle-to-connect-table") == "false") {
    toConnectTableContainer.style.display = "block";
    localStorage.setItem("toggle-to-connect-table", true);
    $("#toConnectTable").DataTable().draw();
  } else if (localStorage.getItem("toggle-to-connect-table") == "true") {
    toConnectTableContainer.style.display = "none";
    localStorage.setItem("toggle-to-connect-table", false);
  }
}

function toggleDelFromMtsTable() {
  let delFromMtsTableContainer = document.getElementById(
    "delFromMtsTableContainer"
  );

  if (localStorage.getItem("toggle-del-from-mts-table") == "false") {
    delFromMtsTableContainer.style.display = "block";
    localStorage.setItem("toggle-del-from-mts-table", true);
    $("#delFromMtsTable").DataTable().draw();
  } else if (localStorage.getItem("toggle-del-from-mts-table") == "true") {
    delFromMtsTableContainer.style.display = "none";
    localStorage.setItem("toggle-del-from-mts-table", false);
  }
}

function toggleAbandonedTable() {
  let abandonedTableContainer = document.getElementById(
    "abandonedTableContainer"
  );

  if (localStorage.getItem("toggle-abandoned-table") == "false") {
    abandonedTableContainer.style.display = "block";
    localStorage.setItem("toggle-abandoned-table", true);
    $("#abandonedTable").DataTable().draw();
  } else if (localStorage.getItem("toggle-abandoned-table") == "true") {
    abandonedTableContainer.style.display = "none";
    localStorage.setItem("toggle-abandoned-table", false);
  }
}

function toggleNoStatementsTable() {
  let noStatementsTableContainer = document.getElementById(
    "noStatementsTableContainer"
  );

  if (localStorage.getItem("toggle-no-statements-table") == "false") {
    noStatementsTableContainer.style.display = "block";
    localStorage.setItem("toggle-no-statements-table", true);
    $("#noStatementsTable").DataTable().draw();
  } else if (localStorage.getItem("toggle-no-statements-table") == "true") {
    noStatementsTableContainer.style.display = "none";
    localStorage.setItem("toggle-no-statements-table", false);
  }
}

function toggleMtsOnlyTable() {
  let mtsOnlyTableContainer = document.getElementById("mtsOnlyTableContainer");

  if (localStorage.getItem("toggle-mts-only-table") == "false") {
    mtsOnlyTableContainer.style.display = "block";
    localStorage.setItem("toggle-mts-only-table", true);
    $("#mtsOnlyTable").DataTable().draw();
  } else if (localStorage.getItem("toggle-mts-only-table") == "true") {
    mtsOnlyTableContainer.style.display = "none";
    localStorage.setItem("toggle-mts-only-table", false);
  }
}

$("#toConnectTable").on("click", ".change-btn", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = toConnectTable.row(e.target.closest("tr")).data();
  let url = `https://web.whatsapp.com/send/?phone=${data.phone}&text&type=phone_number&app_absent=0`;

  console.log(url);
  window.open(url).focus();
});

$("#toConnectTable").on("click", ".delete-btn", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = toConnectTable.row(e.target.closest("tr")).data();
  let url = `/api/employees/fire/${data.name_id}`;

  console.log(url);
  fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        alertsToggle("Успешно уволен!", "success", 4000);
      }
      return Promise.reject(response);
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
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
});

$("#toConnectTable").on("click", ".owntracks-btn", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = toConnectTable.row(e.target.closest("tr")).data();

  let fileName = `config_${data.name}.otrc`;

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
  xmlHttpRequest.open(
    "GET",
    `/api/employees/owntracks/connect/${data.name_id}`
  );
  xmlHttpRequest.setRequestHeader("Content-Type", "text/plain");
  xmlHttpRequest.responseType = "blob";
  xmlHttpRequest.send();
});

$("#delFromMtsTable").on("click", "button", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = delFromMtsTable.row(e.target.closest("tr")).data();
  let url = `/api/mts/subscriber/${data.subscriberID}`;

  console.log(url);
  fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        alertsToggle("Удален успешно!", "success", 4000);
      }
      return Promise.reject(response);
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
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
});

$("#abandonedTable").on("click", "button", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = abandonedTable.row(e.target.closest("tr")).data();
  let url = `/api/employees/fire/${data.name_id}`;

  console.log(url);
  fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        alertsToggle("Успешно уволен!", "success", 4000);
      }
      return Promise.reject(response);
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
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
});

$("#noStatementsTable").on("click", "button", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = noStatementsTable.row(e.target.closest("tr")).data();
  let url = `/api/employees/${data.name_id}`;

  console.log(url);
  fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        alertsToggle("Успешно удален!", "success", 4000);
      }
      return Promise.reject(response);
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
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
});

$("#mtsOnlyTable").on("click", "button", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = mtsOnlyTable.row(e.target.closest("tr")).data();
  let url = `/api/mts/subscriber/${data.subscriberID}`;

  console.log(url);
  fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        alertsToggle("Успешно удален!", "success", 4000);
      }
      return Promise.reject(response);
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
      if (response.status == 403) {
        let currentLocation = location.href.split("/").pop();
        location.href = `/login?next=${currentLocation}`;
      }
    });
});
