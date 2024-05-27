import { alertsToggle } from "../../../v1/alerts.js";
import { hideModal } from "../../../v1/modal.js";
import { dictionary } from "../../../v1/translation_dict.js";
import { checkPattern } from "../../../v1/check_pattern.js";

let employeeTable;
let currentRowOfTable;

// create modal form container
let modalForm = document.createElement("form");
modalForm.id = "modalForm";
modalForm.setAttribute("onSubmit", "return false");

// create modal form inner elements
function createForm() {
  let allFieldsContainer = document.createElement("div");
  allFieldsContainer.id = "allFieldsContainer";

  let nameFieldContainer = document.createElement("div");
  nameFieldContainer.id = "nameFieldContainer";

  let nameFieldLabel = document.createElement("label");
  nameFieldLabel.htmlFor = "nameField";
  nameFieldLabel.innerText = "ФИО сотрудника: ";

  let nameField = document.createElement("input");
  nameField.id = "nameField";
  nameField.type = "text";
  nameField.required = true;

  let phoneFieldContainer = document.createElement("div");
  phoneFieldContainer.id = "phoneFieldContainer";

  let phoneFieldLabel = document.createElement("label");
  phoneFieldLabel.htmlFor = "phoneField";
  phoneFieldLabel.innerText = "Номер телефона: ";

  let phoneField = document.createElement("input");
  phoneField.id = "phoneField";
  phoneField.type = "text";
  phoneField.maxLength = 11;
  phoneField.title = "Формат номера: 79991231122";
  phoneField.required = true;
  phoneField.pattern = "^[7][0-9]{10}";

  let divisionFieldContainer = document.createElement("div");
  divisionFieldContainer.id = "divisionFieldContainer";

  let divisionFieldLabel = document.createElement("label");
  divisionFieldLabel.htmlFor = "divisionField";
  divisionFieldLabel.innerText = "Подразделение:";

  let divisionField = document.createElement("select");
  divisionField.id = "divisionField";
  divisionField.required = true;

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

  let dateFields = document.createElement("div");
  dateFields.id = "dateFields";

  let hireDateLabel = document.createElement("label");
  hireDateLabel.htmlFor = "hireDateField";
  hireDateLabel.innerText = "Дата приема:";

  let quitDateLabel = document.createElement("label");
  quitDateLabel.htmlFor = "quitDateField";
  quitDateLabel.innerText = "Дата увольнения:";

  let hireDateField = document.createElement("input");
  hireDateField.id = "hireDateField";
  hireDateField.type = "date";
  hireDateField.required = true;

  let quitDateField = document.createElement("input");
  quitDateField.id = "quitDateField";
  quitDateField.type = "date";

  let scheduleField = document.createElement("div");
  scheduleField.id = "scheduleField";

  let scheduleCheck = document.createElement("input");
  scheduleCheck.id = "scheduleCheck";
  scheduleCheck.type = "checkbox";

  let scheduleCheckLabel = document.createElement("label");
  scheduleCheckLabel.htmlFor = "scheduleCheck";
  scheduleCheckLabel.innerText = "Сотрудник является ванщиком";

  let stafferContainer = document.createElement("div");
  stafferContainer.id = "stafferContainer";

  let stafferCheckLabel = document.createElement("label");
  stafferCheckLabel.id = "stafferCheckLabel";
  stafferCheckLabel.htmlFor = "stafferCheck";
  stafferCheckLabel.innerText = "Устроен по ТК";

  let stafferCheck = document.createElement("input");
  stafferCheck.id = "stafferCheck";
  stafferCheck.type = "checkbox";

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

  nameFieldContainer.append(nameFieldLabel, nameField);
  phoneFieldContainer.append(phoneFieldLabel, phoneField);
  divisionFieldContainer.append(divisionFieldLabel, divisionField);
  restFields.append(dateFields, scheduleField, stafferContainer);
  dateFields.append(hireDateLabel, hireDateField, quitDateLabel, quitDateField);
  scheduleField.append(scheduleCheck, scheduleCheckLabel);
  stafferContainer.append(stafferCheck, stafferCheckLabel);
  btnsContainer.append(cancelBtn, saveBtn);

  allFieldsContainer.append(
    nameFieldContainer,
    phoneFieldContainer,
    divisionFieldContainer,
    restFields
  );

  modalForm.append(allFieldsContainer, btnsContainer);

  return modalForm;
}
// creating table
$.ajax({
  url: "/api/employees",
  method: "GET",
  contentType: "application/json",
})
  .done(function (data) {
    console.log(data);
    employeeTable = new DataTable("#employeeTable", {
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
      buttons: [
        {
          //add new-employee button
          text: "Новый сотрудник",
          className: "new-emp-btn",
          attr: {
            id: "addNewEmployee",
          },
          action: function () {
            modal.style.display = "flex";
            modalTitle.innerText = "Добавить сотрудника";
            createForm();
            modalBody.appendChild(modalForm);

            let hireDateField = document.getElementById("hireDateField");
            let date = new Date().toISOString().split("T")[0];

            hireDateField.value = date;

            document.getElementById("saveBtn").onclick = createEmployee;
          },
        },
      ],

      columns: [
        { data: "division_name" },
        { data: "name" },
        { data: "phone" },
        { data: "schedule_name" },
        { data: "hire_date" },
        { data: "quit_date" },
        {
          data: "staffer",
          render: function (data) {
            return data ? "Да" : "";
          },
        },
        {
          // add column with change buttons to all rows in table
          data: null,
          defaultContent: "<button class='change-btn'>Изменить</button>",
          targets: -1,
        },
      ],
    });

    $("#preLoadContainer")[0].style.display = "none";
    $("#tableContainer")[0].style.opacity = 1;
    $("#employeeTable").DataTable().draw();

    // When change button is clicked, create modal,
    // add delete button in form, fill form with api data
    employeeTable.on("click", "button", function (e) {
      currentRowOfTable = e.target.closest("tr");
      let data = employeeTable.row(e.target.closest("tr")).data();

      modal.style.display = "flex";
      modalTitle.innerText = `Изменить сотрудника ${
        data.tracking_type ? data.tracking_type : ""
      }  ${localStorage.getItem("rang-id") == 1 ? " ID: " + data.name_id : ""}`;
      modalForm = createForm();
      modalBody.appendChild(modalForm);

      let quitDateField = document.getElementById("quitDateField");
      quitDateField.disabled = true;
      quitDateField.title =
        "Чтобы уволить сотрудника, проставьте 'У' в таблице";

      let ownTracksBtn = document.createElement("button");
      ownTracksBtn.id = "ownTracksBtn";
      ownTracksBtn.type = "button";
      ownTracksBtn.innerText = "OwnTracks+";
      ownTracksBtn.addEventListener("click", () => {
        downloadOwnTarcksConfig(data.name, data.name_id);
      });

      document.getElementById("scheduleField").append(ownTracksBtn);

      let deleteAccess = localStorage.getItem("rang-id");
      if (deleteAccess == "1") {
        let deleteBtn = document.createElement("button");
        deleteBtn.id = "deleteBtn";
        deleteBtn.type = "button";
        deleteBtn.innerText = "Удалить";
        deleteBtn.onclick = deleteEmployee;

        document.getElementById("stafferContainer").append(deleteBtn);
      }

      let name = document.getElementById("nameField");
      name.setAttribute("name-id", data.name_id);
      let phone = document.getElementById("phoneField");
      let options = document.getElementById("divisionField").childNodes;
      let hireDate = document.getElementById("hireDateField");
      let quitDate = document.getElementById("quitDateField");
      let scheduleCheck = document.getElementById("scheduleCheck");
      let stafferCheck = document.getElementById("stafferCheck");
      let saveBtn = document.getElementById("saveBtn");

      name.value = data.name;
      phone.value = data.phone;
      options.forEach((o) =>
        data.division_name === o.innerText ? (o.selected = true) : null
      );
      hireDate.value = data.hire_date;
      quitDate.value = data.quit_date;
      data.schedule == 2 ? (scheduleCheck.checked = true) : null;
      stafferCheck.checked = data.staffer;

      saveBtn.onclick = changeEmployee;
    });
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

const closeModal = document.getElementById("closeModal");
const modal = document.getElementById("modalContainer");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");

closeModal.addEventListener("click", hideModal);

// collect new employee fields data
function createEmployee(e) {
  let name = document.getElementById("nameField").value;
  let phone = document.getElementById("phoneField");

  let options = document.getElementById("divisionField");
  let divisionId =
    options.options[options.selectedIndex].getAttribute("division_id");

  let hireDate = document.getElementById("hireDateField").value;

  let quitDate = document.getElementById("quitDateField").value;

  let scheduleCheck = document.getElementById("scheduleCheck").checked;

  // let noTrackingCheck = document.getElementById("noTrackingCheck").checked;

  let stafferCheck = document.getElementById("stafferCheck").checked;

  if (
    name == "" ||
    phone.value == "" ||
    !checkPattern("phoneField") ||
    phone.value.length != 11 ||
    hireDate == ""
  ) {
    return;
  }
  let parameters = {
    name: name,
    phone: phone.value,
    division: divisionId,
    hire_date: hireDate,
    staffer: stafferCheck,
  };
  // no_tracking: noTrackingCheck,

  quitDate ? (parameters["quit_date"] = quitDate) : null;

  !scheduleCheck ? 1 : (parameters["schedule"] = 2);

  sendNewEmployee(parameters);
}

// send new employee data to api and get responses
async function sendNewEmployee(parameters) {
  await fetch("/api/employees", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.status === 201) {
        return response.json();
      }
      return Promise.reject(response);
    })
    .then((data) => {
      hideModal();
      alertsToggle("Сотрудник добавлен!", "success", 2500);
      $("#employeeTable").DataTable().row.add(data).draw();
    })

    .catch((response) => {
      if (response.status == 422) {
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
      if (response.status == 500) {
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

// collect edit employee fields data
function changeEmployee() {
  let name = document.getElementById("nameField").value;
  let phone = document.getElementById("phoneField").value;

  let options = document.getElementById("divisionField");
  let divisionId =
    options.options[options.selectedIndex].getAttribute("division_id");

  let hireDate = document.getElementById("hireDateField").value;

  let quitDate = document.getElementById("quitDateField").value;

  let scheduleCheck = document.getElementById("scheduleCheck").checked;

  // let noTrackingCheck = document.getElementById("noTrackingCheck").checked;

  let stafferCheck = document.getElementById("stafferCheck").checked;

  if (
    name == "" ||
    phone == "" ||
    !checkPattern("phoneField") ||
    phone.length != 11 ||
    hireDate == ""
  )
    return;

  let parameters = {
    name: name,
    phone: phone,
    division: divisionId,
    hire_date: hireDate,
    quit_date: quitDate == "" ? null : quitDate,
    schedule: !scheduleCheck ? 1 : 2,
    staffer: stafferCheck,
  };
  // no_tracking: noTrackingCheck,

  sendEditEmployee(parameters);
}

// send edit employee data to api and get responses
function sendEditEmployee(parameters) {
  let nameId = document.getElementById("nameField").getAttribute("name-id");
  fetch(`/api/employees/${nameId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.status === 200) {
        return response.json();
      }

      return Promise.reject(response);
    })
    .then((data) => {
      hideModal();
      alertsToggle("Сотрудник изменен!", "success", 2500);
      $("#employeeTable").DataTable().row(currentRowOfTable).data(data).draw();
      currentRowOfTable = null;
    })
    .catch((response) => {
      if (response.status === 404) {
        alertsToggle("Сотрудник не найден!", "danger", 3000);
      }
      if (response.status === 422) {
        response.json().then((json) => {
          Object.values(json.detail).forEach((d) => {
            let splitD = d.split(":");
            let nameField = splitD[0];
            let newNameField = dictionary[nameField]
              ? dictionary[nameField]
              : nameField;
            let newD = newNameField + ": " + splitD[1];
            alertsToggle(newD, "danger", 3000);
          });
        });
      }
      if (response.status == 500) {
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

// send delete employee name_id to api and get responses
function deleteEmployee() {
  let nameId = document.getElementById("nameField").getAttribute("name-id");
  if (!confirm("Действительно хотите удалить сотрудника?")) return;
  fetch(`/api/employees/${nameId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (response.status === 204) {
        $("#employeeTable").DataTable().row(currentRowOfTable).remove().draw();
        currentRowOfTable = null;
        hideModal();
        alertsToggle("Сотрудник удален!", "success", 2500);
      }
      return Promise.reject(response);
    })
    .catch((error) => {
      if (error.status === 403) {
        alertsToggle("Отказано в доступе!", "danger", 3000);
      }
      if (error.status === 404) {
        alertsToggle("Сотрудник не найден!", "danger", 3000);
      }
      if (error.status == 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}

function downloadOwnTarcksConfig(name, name_id) {
  let fileName = `config_${name}.otrc`;

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
  xmlHttpRequest.open("GET", `/api/employees/owntracks/connect/${name_id}`);
  xmlHttpRequest.setRequestHeader("Content-Type", "text/plain");
  xmlHttpRequest.responseType = "blob";
  xmlHttpRequest.send();
}
