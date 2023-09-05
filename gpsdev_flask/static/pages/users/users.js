// import { alertsToggle } from "../../alerts";
// import { dictionary } from "../../translation_dict";

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
  passwordField.type = "password";

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

    let divisionCheck = document.createElement("input");
    divisionCheck.type = "checkbox";
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

closeModal.addEventListener("click", hideModal);

// clear and hide Modal
function hideModal() {
  modal.style.display = "none";
  modalTitle.innerText = "";
  modalBody.innerHTML = "";
  modalForm.innerHTML = "";
}
