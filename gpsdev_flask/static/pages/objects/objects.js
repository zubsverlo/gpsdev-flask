import { alertsToggle } from "../../alerts.js";
import { dictionary } from "../../translation_dict.js";

let objectTable;

const closeModal = document.getElementById("closeModal");
const modal = document.getElementById("modalContainer");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");

// create modal form container
let modalForm = document.createElement("form");
modalForm.id = "modalForm";
modalForm.setAttribute("onSubmit", "return false");

// create modal form inner elements
function createForm() {
  let nameFieldContainer = document.createElement("div");
  nameFieldContainer.id = "nameFieldContainer";

  let nameFieldLabel = document.createElement("label");
  nameFieldLabel.htmlFor = "nameField";
  nameFieldLabel.innerText = "ФИО подопечного: ";

  let nameField = document.createElement("input");
  nameField.id = "nameField";
  nameField.type = "text";
  nameField.required = true;

  let phoneFieldContainer = document.createElement("div");
  phoneFieldContainer.id = "phoneFieldContainer";

  let phoneFieldLabel = document.createElement("label");
  phoneFieldLabel.htmlFor = "phoneField";
  phoneFieldLabel.innerText = "Контактные данные: ";

  let phoneField = document.createElement("textarea");
  phoneField.id = "phoneField";
  phoneField.cols = "51";
  phoneField.rows = "3";

  let addressFieldContainer = document.createElement("div");
  addressFieldContainer.id = "addressFieldContainer";

  let addressFieldLabel = document.createElement("label");
  addressFieldLabel.id = "addressFieldLabel";
  addressFieldLabel.innerText = "Адрес подопечного: ";

  let addressField = document.createElement("input");
  addressField.id = "addressField";
  addressField.type = "text";
  addressField.placeholder = "Начните вводить адрес";
  addressField.required = true;

  let addressSelectContainer = document.createElement("div");
  addressSelectContainer.id = "addressSelectContainer";
  addressSelectContainer.style.display = "none";

  let addressSelect = document.createElement("select");
  addressSelect.id = "addressSelect";

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

  let activeField = document.createElement("div");
  activeField.id = "activeField";

  let activeCheck = document.createElement("input");
  activeCheck.id = "activeCheck";
  activeCheck.type = "checkbox";

  let activeCheckLabel = document.createElement("label");
  activeCheckLabel.htmlFor = "activeCheck";
  activeCheckLabel.innerText = "Показывать в списке для заполнения шахматки";

  let noPaymentField = document.createElement("div");
  noPaymentField.id = "noPaymentField";

  let noPaymentCheck = document.createElement("input");
  noPaymentCheck.id = "noPaymentCheck";
  noPaymentCheck.type = "checkbox";

  let noPaymentCheckLabel = document.createElement("label");
  noPaymentCheckLabel.htmlFor = "noPaymentCheck";
  noPaymentCheckLabel.innerText = "Частично платная основа, но не доплачивает";

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
  addressFieldContainer.append(addressFieldLabel, addressField);
  addressSelectContainer.append(addressSelect);
  divisionFieldContainer.append(divisionFieldLabel, divisionField);
  restFields.append(activeField, noPaymentField);
  activeField.append(activeCheck, activeCheckLabel);
  noPaymentField.append(noPaymentCheck, noPaymentCheckLabel);
  btnsContainer.append(cancelBtn, saveBtn);

  modalForm.append(
    nameFieldContainer,
    divisionFieldContainer,
    restFields,
    phoneFieldContainer,
    addressFieldContainer,
    addressSelectContainer,
    btnsContainer
  );

  return modalForm;
}

// $.ajax({
//   url: "/api/objects",
//   method: "GET",
//   contentType: "application/json",
// }).done(function (data) {
//   let windowHeight = window.innerHeight - 220;
//   objectTable = new DataTable("#objectTable", {
//     aaData: data,
//     scrollY: windowHeight,
//     scrollX: "100%",
//     scrollCollapse: true,
//     paging: false,
//     language: {
//       search: "Поиск: ",
//       info: "Найдено по запросу: _TOTAL_ ",
//       infoFiltered: "( из _MAX_ записей )",
//       infoEmpty: "",
//       zeroRecords: "Совпадений не найдено",
//     },
//     dom: "<'pre-table-row'<'new-obj-container'B>f>rtip",
//     buttons: [
//       {
//         //add new-object button
//         text: "Новый подопечный",
//         className: "new-obj-btn",
//         attr: {
//           id: "addNewObject",
//         },
//         action: function () {
//           modal.style.display = "flex";
//           modalTitle.innerText = "Добавить подопечного";
//           createForm();
//           modalBody.appendChild(modalForm);
//           // let hireDateField = document.getElementById("hireDateField");
//           // let date = new Date().toISOString().split("T")[0];
//           // hireDateField.value = date;
//           // document.getElementById("saveBtn").onclick = createEmployee;
//         },
//       },
//     ],

//     columns: [
//       { data: "division_name" },
//       { data: "name" },
//       { data: "address" },
//       { data: "phone" },
//       {
//         // add column with change buttons to all rows in table
//         data: null,
//         defaultContent: "<button class='change-btn'>Изменить</button>",
//         targets: -1,
//       },
//     ],
//   });

//   $("#preLoadContainer")[0].style.display = "none";
//   $("#tableContainer")[0].style.opacity = 1;
// });

createForm();
modalTitle.innerText = "Добавить подопечного";
modalBody.appendChild(modalForm);

closeModal.addEventListener("click", hideModal);

// clear and hide Modal
function hideModal() {
  modal.style.display = "none";
  modalTitle.innerText = "";
  modalBody.innerHTML = "";
  modalForm.innerHTML = "";
}
