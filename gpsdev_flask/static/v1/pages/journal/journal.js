import { alertsToggle } from "../../../v1/alerts.js";
import { hideModal } from "../../../v1/modal.js";
import { dictionary } from "../../../v1/translation_dict.js";

let journalTable;
let currentRowOfTable;

const closeModal = document.getElementById("closeModal");
const modal = document.getElementById("modalContainer");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");

// create modal form container
let modalForm = document.createElement("form");
modalForm.id = "modalForm";
modalForm.autocomplete = "off";
modalForm.setAttribute("onSubmit", "return false");

// create modal form inner elements
function createForm() {
  let entryIdFieldContainer = document.createElement("div");
  entryIdFieldContainer.id = "entryIdFieldContainer";

  let entryIdFieldLabel = document.createElement("label");
  entryIdFieldLabel.id = "entryIdFieldLabel";
  entryIdFieldLabel.innerText = `ID Записи: `;

  let nameFieldContainer = document.createElement("div");
  nameFieldContainer.id = "nameFieldContainer";

  let nameFieldLabel = document.createElement("label");
  nameFieldLabel.htmlFor = "nameField";
  nameFieldLabel.innerText = "ФИО сотрудника: ";

  let nameField = document.createElement("input");
  nameField.id = "nameField";
  nameField.type = "text";
  nameField.disabled = true;

  let subIdFieldContainer = document.createElement("div");
  subIdFieldContainer.id = "subIdFieldContainer";

  let subIdFieldLabel = document.createElement("label");
  subIdFieldLabel.htmlFor = "subIdFieldLabel";
  subIdFieldLabel.innerText = "Sub ID: ";

  let subIdField = document.createElement("input");
  subIdField.id = "subIdField";
  subIdField.type = "text";
  subIdField.disabled = true;

  let dateFields = document.createElement("div");
  dateFields.id = "dateFields";

  let initDateFieldContainer = document.createElement("div");
  initDateFieldContainer.id = "initDateFieldContainer";

  let initDateField = document.createElement("input");
  initDateField.id = "initDateField";
  initDateField.type = "date";

  let initDateFieldLabel = document.createElement("label");
  initDateFieldLabel.htmlFor = "initDateField";
  initDateFieldLabel.innerText = "Дата начала:";

  let endDateFieldContainer = document.createElement("div");
  endDateFieldContainer.id = "endDateFieldContainer";

  let endDateField = document.createElement("input");
  endDateField.id = "endDateField";
  endDateField.type = "date";

  let endDateFieldLabel = document.createElement("label");
  endDateFieldLabel.htmlFor = "endDateField";
  endDateFieldLabel.innerText = "Дата конца:";

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

  entryIdFieldContainer.append(entryIdFieldLabel);
  nameFieldContainer.append(nameFieldLabel, nameField);
  subIdFieldContainer.append(subIdFieldLabel, subIdField);
  dateFields.append(
    initDateFieldLabel,
    initDateField,
    endDateFieldLabel,
    endDateField
  );

  btnsContainer.append(cancelBtn, saveBtn);

  modalForm.append(
    entryIdFieldContainer,
    nameFieldContainer,
    subIdFieldContainer,
    dateFields,
    btnsContainer
  );

  return modalForm;
}

$.ajax({
  url: "/api/journal",
  method: "GET",
  contentType: "application/json",
})
  .done(function (data) {
    journalTable = new DataTable("#journalTable", {
      aaData: data,
      scrollY: "70vh",
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
      dom: "<'pre-table-row'f>rtip",
      columns: [
        { data: "id" },
        { data: "name_id" },
        { data: "name" },
        { data: "subscriberID" },
        { data: "period_init" },
        { data: "period_end" },
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
    $("#journalTable").DataTable().draw();
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

$("#journalTable").on("click", "button", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = journalTable.row(e.target.closest("tr")).data();

  modal.style.display = "flex";
  modalTitle.innerText = `Изменение периода ${
    localStorage.getItem("rang-id") == 1 ? " Name ID: " + data.name_id : ""
  }`;
  modalForm = createForm();
  modalBody.appendChild(modalForm);

  let deleteAccess = localStorage.getItem("rang-id");
  if (deleteAccess == "1") {
    let deleteBtn = document.createElement("button");
    deleteBtn.id = "deleteBtn";
    deleteBtn.type = "button";
    deleteBtn.innerText = "Удалить";
    deleteBtn.onclick = deletePeriod;

    document
      .getElementById("btnsContainer")
      .insertBefore(deleteBtn, document.getElementById("saveBtn"));
  }

  let entryId = document.getElementById("entryIdFieldLabel");
  let name = document.getElementById("nameField");
  name.setAttribute("name-id", data.name_id);
  name.setAttribute("row-id", data.id);
  let subId = document.getElementById("subIdField");
  let initDate = document.getElementById("initDateField");
  let endDate = document.getElementById("endDateField");
  let saveBtn = document.getElementById("saveBtn");

  entryId.innerText = `ID Записи: ${data.id}`;
  name.value = data.name;
  subId.value = data.subscriberID;
  initDate.value = data.period_init;
  endDate.value = data.period_end;

  saveBtn.onclick = changePeriod;
});

closeModal.addEventListener("click", hideModal);

// collect edited row with period fields data
function changePeriod() {
  let nameId = document.getElementById("nameField").getAttribute("name-id");
  let subId = document.getElementById("subIdField").value;
  let initDate = document.getElementById("initDateField").value;
  let endDate = document.getElementById("endDateField").value;

  if (initDate == "") return;

  let parameters = {
    name_id: nameId,
    period_init: initDate,
    subscriberID: subId,
  };

  endDate ? (parameters["period_end"] = endDate) : null;

  sendPeriod(parameters);
}

// send period data to api and get responses
function sendPeriod(parameters) {
  let entryId = document.getElementById("nameField").getAttribute("row-id");
  fetch(`/api/journal/${entryId}`, {
    method: "PATCH",
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
      data["id"] = entryId;
      data["name"] = document.getElementById("nameField").value;
      hideModal();
      alertsToggle("Данные успешно изменены!", "success", 2500);
      $("#journalTable").DataTable().row(currentRowOfTable).data(data).draw();
      currentRowOfTable = null;
    })
    .catch((response) => {
      if (response.status === 404) {
        alertsToggle("Запись не найдена!", "danger", 3000);
      }
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

// send delete entry row_id to api and get responses
function deletePeriod() {
  let entryId = document.getElementById("nameField").getAttribute("row-id");
  if (!confirm("Дейсвительно хотите удалить запись?")) return;
  fetch(`/api/journal/${entryId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.status === 204) {
        hideModal();
        alertsToggle("Запись удалена!", "success", 2500);
        $("#journalTable").DataTable().row(currentRowOfTable).remove().draw();
        currentRowOfTable = null;
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 403) {
        alertsToggle("Отказано в доступе!", "danger", 3000);
      }
      if (response.status === 404) {
        alertsToggle("Запись не найден!", "danger", 3000);
      }
      if (response.status == 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}
