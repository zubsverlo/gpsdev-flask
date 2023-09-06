import { alertsToggle } from "../../alerts.js";
import { dictionary } from "../../translation_dict.js";

let usersTable;
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
  let nameFieldContainer = document.createElement("div");
  nameFieldContainer.id = "nameFieldContainer";

  let nameFieldLabel = document.createElement("label");
  nameFieldLabel.htmlFor = "nameField";
  nameFieldLabel.innerText = "Имя пользователя: ";

  let nameField = document.createElement("input");
  nameField.id = "nameField";
  nameField.type = "text";
  nameField.required = true;

  let phoneFieldContainer = document.createElement("div");
  phoneFieldContainer.id = "phoneFieldContainer";

  let phoneFieldLabel = document.createElement("label");
  phoneFieldLabel.htmlFor = "phoneField";
  phoneFieldLabel.innerText = "Номер для доступа в аккаунт: ";

  let phoneField = document.createElement("input");
  phoneField.id = "phoneField";
  phoneField.type = "text";
  phoneField.maxLength = 11;
  phoneField.title = "Формат номера: 79991231122";
  phoneField.required = true;
  phoneField.pattern = "^[7][0-9]{10}";

  let passwordFieldContainer = document.createElement("div");
  passwordFieldContainer.id = "passwordFieldContainer";

  let passwordFieldLabel = document.createElement("label");
  passwordFieldLabel.htmlFor = "passwordFieldLabel";
  passwordFieldLabel.innerText = "Пароль: ";

  let passwordField = document.createElement("input");
  passwordField.id = "passwordField";
  passwordField.type = "text";
  passwordField.required = true;

  let rangFieldContainer = document.createElement("div");
  rangFieldContainer.id = "rangFieldContainer";

  let rangFieldLabel = document.createElement("label");
  rangFieldLabel.htmlFor = "rangFieldLabel";
  rangFieldLabel.innerText = "Ранг пользователя:";

  let rangField = document.createElement("select");
  rangField.id = "rangField";
  rangField.required = true;

  let rangOption1 = document.createElement("option");
  rangOption1.id = "rangOption1";
  rangOption1.setAttribute("rang-id", 1);
  rangOption1.innerText = "Администратор";

  let rangOption2 = document.createElement("option");
  rangOption2.id = "rangOption2";
  rangOption2.setAttribute("rang-id", 2);
  rangOption2.innerText = "Руководитель";

  let rangOption3 = document.createElement("option");
  rangOption3.id = "rangOption3";
  rangOption3.setAttribute("rang-id", 3);
  rangOption3.innerText = "Куратор";

  let rangOption4 = document.createElement("option");
  rangOption4.id = "rangOption4";
  rangOption4.setAttribute("rang-id", 4);
  rangOption4.innerText = "Сотрудник";

  let divisionsContainer = document.createElement("div");
  divisionsContainer.id = "divisionsContainer";

  let divisions = JSON.parse(localStorage.getItem("access"));
  divisions.forEach((d) => {
    const divisionName = d.division;
    let division = document.createElement("div");
    division.id = "division" + "-" + d.division_id;

    let divisionLabel = document.createElement("label");
    divisionLabel.id = "divisionLabel" + "-" + d.division_id;
    divisionLabel.innerText = divisionName;
    divisionLabel.htmlFor = "divisionCheck" + "-" + d.division_id;

    let divisionCheck = document.createElement("input");
    divisionCheck.type = "checkbox";
    divisionCheck.id = "divisionCheck" + "-" + d.division_id;
    divisionCheck.setAttribute("division_id", d.division_id);

    division.append(divisionLabel, divisionCheck);
    divisionsContainer.appendChild(division);
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

  nameFieldContainer.append(nameFieldLabel, nameField);
  phoneFieldContainer.append(phoneFieldLabel, phoneField);
  passwordFieldContainer.append(passwordFieldLabel, passwordField);
  rangField.append(rangOption1, rangOption2, rangOption3, rangOption4);
  rangFieldContainer.append(rangFieldLabel, rangField);
  btnsContainer.append(cancelBtn, saveBtn);

  modalForm.append(
    nameFieldContainer,
    phoneFieldContainer,
    passwordFieldContainer,
    rangFieldContainer,
    divisionsContainer,
    btnsContainer
  );

  return modalForm;
}

$.ajax({
  url: "/api/users",
  method: "GET",
  contentType: "application/json",
}).done(function (data) {
  console.log(data);
  data.forEach((user) => {
    let newArray = [];
    user.access.forEach((d) => {
      newArray.push(d.division);
    });
    let result = newArray.join(", ");
    user["divisions"] = result;
  });
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
          modal.style.display = "flex";
          modalTitle.innerText = "Добавить пользователя";
          createForm();
          modalBody.appendChild(modalForm);

          document.getElementById("saveBtn").onclick = createUser;
        },
      },
    ],

    columns: [
      { data: "id" },
      { data: "name" },
      { data: "phone" },
      { data: "divisions" },
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

$("#usersTable").on("click", "button", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = usersTable.row(e.target.closest("tr")).data();
  console.log(data);

  modal.style.display = "flex";
  modalTitle.innerText = `Изменить пользователя ${
    localStorage.getItem("rang-id") == 1 ? " ID: " + data.id : ""
  }`;
  modalForm = createForm();
  modalBody.appendChild(modalForm);

  let deleteAccess = localStorage.getItem("rang-id");
  if (deleteAccess == "1") {
    let deleteBtn = document.createElement("button");
    deleteBtn.id = "deleteBtn";
    deleteBtn.type = "button";
    deleteBtn.innerText = "Удалить";
    deleteBtn.onclick = deleteUser;

    document
      .getElementById("btnsContainer")
      .insertBefore(deleteBtn, document.getElementById("saveBtn"));
  }

  let name = document.getElementById("nameField");
  name.setAttribute("user-id", data.id);
  let phone = document.getElementById("phoneField");
  let password = document.getElementById("passwordField");
  let rang = document.getElementById("rangField").childNodes;
  let divisions = document.getElementById("divisionsContainer").childNodes;
  let saveBtn = document.getElementById("saveBtn");

  name.value = data.name;
  phone.value = data.phone;
  password.required = false;
  rang.forEach((r) => (data.rang === r.innerText ? (r.selected = true) : null));
  divisions.forEach((c) => {
    data.access.forEach((a) => {
      c.childNodes[0].innerText == a.division
        ? (c.childNodes[1].checked = true)
        : null;
    });
  });

  saveBtn.onclick = changeUser;
});

closeModal.addEventListener("click", hideModal);

// clear and hide Modal
function hideModal() {
  modal.style.display = "none";
  modalTitle.innerText = "";
  modalBody.innerHTML = "";
  modalForm.innerHTML = "";
}

function createUser() {
  let name = document.getElementById("nameField").value;
  let phone = document.getElementById("phoneField").value;
  let password = document.getElementById("passwordField").value;

  let rang = document.getElementById("rangField");
  let rangId = rang.options[rang.selectedIndex].getAttribute("rang-id");

  let divisions = document.getElementById("divisionsContainer");

  let divisionList = [];

  divisions.childNodes.forEach((c) => {
    c.childNodes[1].checked
      ? divisionList.push(c.childNodes[1].getAttribute("division_id"))
      : null;
  });

  if (name == "" || phone == "" || password == "") {
    return;
  }

  let parameters = {
    access_set: divisionList,
    name: name,
    phone: phone,
    password: password,
    rang_id: rangId,
  };

  console.log(parameters);

  sendNewUser(parameters);
}

function sendNewUser(parameters) {
  fetch("/api/users", {
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
      console.log("this is data: ", data);
      let newArray = [];
      data.access.forEach((d) => {
        newArray.push(d.division);
      });
      let result = newArray.join(", ");
      data["divisions"] = result;

      hideModal();
      alertsToggle("Новый пользователь добавлен!", "success", 2500);
      $("#usersTable").DataTable().row(currentRowOfTable).add(data).draw();
      currentRowOfTable = null;
      newArray = [];
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
    });
}

function changeUser() {
  let name = document.getElementById("nameField").value;
  let phone = document.getElementById("phoneField").value;
  let password = document.getElementById("passwordField").value;

  let rang = document.getElementById("rangField");
  let rangId = rang.options[rang.selectedIndex].getAttribute("rang-id");

  let divisions = document.getElementById("divisionsContainer");

  let divisionList = [];

  divisions.childNodes.forEach((c) => {
    c.childNodes[1].checked
      ? divisionList.push(c.childNodes[1].getAttribute("division_id"))
      : null;
  });

  if (name == "" || phone == "") {
    return;
  }

  let parameters = {
    access_set: divisionList,
    name: name,
    phone: phone,
    rang_id: rangId,
  };

  password ? (parameters["password"] = password) : null;

  console.log(parameters);

  sendEditUser(parameters);
}

function sendEditUser(parameters) {
  let userID = document.getElementById("nameField").getAttribute("user-id");
  console.log(userID);
  fetch(`/api/users/${userID}`, {
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
      let newArray = [];
      data.access.forEach((d) => {
        newArray.push(d.division);
      });
      let result = newArray.join(", ");
      data["divisions"] = result;

      hideModal();
      alertsToggle("Пользователь изменен!", "success", 2500);
      $("#usersTable").DataTable().row(currentRowOfTable).add(data).draw();
      currentRowOfTable = null;
      newArray = [];
    })
    .catch((response) => {
      if (response.status === 404) {
        alertsToggle("Пользователь не найден!", "danger", 3000);
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
    });
}

function deleteUser() {
  let userID = document.getElementById("nameField").getAttribute("user-id");
  console.log(currentRowOfTable);
  if (!confirm("Действительно хотите удалить пользователя?")) return;
  fetch(`/api/users/${userID}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.ok) {
        hideModal();
        alertsToggle("Пользователь удален!", "success", 2500);
        $("#usersTable").DataTable().row(currentRowOfTable).remove().draw();
        console.log("current", currentRowOfTable);
        currentRowOfTable = null;
        console.log("current clear", currentRowOfTable);
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 403) {
        alertsToggle("Отказано в доступе!", "danger", 3000);
      }
      if (response.status === 404) {
        alertsToggle("Пользователь не найден!", "danger", 3000);
      }
    });
}
