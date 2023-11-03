import { alertsToggle } from "../../alerts.js";
import { hideModal } from "../../modal.js";
import { dictionary } from "../../translation_dict.js";

let objectTable;
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
  nameFieldLabel.innerText = "ФИО подопечного: ";

  let nameField = document.createElement("input");
  nameField.id = "nameField";
  nameField.type = "text";
  nameField.required = true;

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
  activeCheck.checked = "true";

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

  let dateFieldsContainer = document.createElement("div");
  dateFieldsContainer.id = "dateFieldsContainer";

  let startDateContainer = document.createElement("div");
  startDateContainer.id = "startDateContainer";

  let startDateLabel = document.createElement("label");
  startDateLabel.id = "startDateLabel";
  startDateLabel.innerText = "Дата приема на обслуж.";
  startDateLabel.htmlFor = "startDateField";

  let startDateField = document.createElement("input");
  startDateField.id = "startDateField";
  startDateField.type = "date";

  let endDateContainer = document.createElement("div");
  endDateContainer.id = "endDateContainer";

  let endDateLabel = document.createElement("label");
  endDateLabel.id = "endDateLabel";
  endDateLabel.innerText = "Дата снятия с обслуж.";
  endDateLabel.htmlFor = "endDateField";

  let endDateField = document.createElement("input");
  endDateField.id = "endDateField";
  endDateField.type = "date";

  let phoneFieldContainer = document.createElement("div");
  phoneFieldContainer.id = "phoneFieldContainer";

  let phoneFieldLabel = document.createElement("label");
  phoneFieldLabel.htmlFor = "phoneField";
  phoneFieldLabel.innerText = "Контактные данные: ";

  let phoneField = document.createElement("textarea");
  phoneField.id = "phoneField";
  phoneField.cols = "49";
  phoneField.rows = "3";

  let addressFieldContainer = document.createElement("div");
  addressFieldContainer.id = "addressFieldContainer";

  let switchAddressContainer = document.createElement("div");
  switchAddressContainer.id = "switchAddressContainer";

  let switchAddressLabelName = document.createElement("label");
  switchAddressLabelName.id = "switchAddressLabelName";
  switchAddressLabelName.innerText = "Изменить источник адресов: ";

  let switchAddressLabel = document.createElement("label");
  switchAddressLabel.id = "switchAddressLabel";

  let switchAddressBtn = document.createElement("input");
  switchAddressBtn.id = "switchAddressBtn";
  switchAddressBtn.type = "checkbox";
  if (localStorage.getItem("address-sorce") === "1") {
    switchAddressBtn.checked = false;
  } else if (localStorage.getItem("address-sorce") === "2") {
    switchAddressBtn.checked = true;
  } else {
    switchAddressBtn.checked = true;
  }

  let switchAddressSpan = document.createElement("span");
  switchAddressSpan.id = "switchAddressSpan";
  switchAddressSpan.onclick = switchAddress;

  let addressFieldLabel = document.createElement("label");
  addressFieldLabel.id = "addressFieldLabel";
  addressFieldLabel.innerText = "Адрес подопечного: ";

  let addressField = document.createElement("input");
  addressField.id = "addressField";
  addressField.type = "text";
  addressField.setAttribute("list", "addressSelect");
  addressField.placeholder = "Начните вводить адрес";
  addressField.required = true;

  let apartmentFieldContainer = document.createElement("div");
  apartmentFieldContainer.id = "apartmentFieldContainer";

  let apartmentFieldLabel = document.createElement("label");
  apartmentFieldLabel.id = "apartmentFieldLabel";
  apartmentFieldLabel.innerText = "Номер квартиры, подъезд, код домофона и т.д";
  apartmentFieldLabel.htmlFor = "";

  let apartmentField = document.createElement("input");
  apartmentField.id = "apartmentField";
  apartmentField.type = "text";

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
  switchAddressLabel.append(switchAddressBtn, switchAddressSpan);
  switchAddressContainer.append(switchAddressLabelName, switchAddressLabel);
  startDateContainer.append(startDateLabel, startDateField);
  endDateContainer.append(endDateLabel, endDateField);
  phoneFieldContainer.append(phoneFieldLabel, phoneField);
  addressFieldContainer.append(
    addressFieldLabel,
    addressField,
    switchAddressContainer
  );
  apartmentFieldContainer.append(apartmentFieldLabel, apartmentField);

  divisionFieldContainer.append(divisionFieldLabel, divisionField);
  restFields.append(activeField, noPaymentField);
  activeField.append(activeCheck, activeCheckLabel);
  noPaymentField.append(noPaymentCheck, noPaymentCheckLabel);
  dateFieldsContainer.append(startDateContainer, endDateContainer);
  btnsContainer.append(cancelBtn, saveBtn);

  modalForm.append(
    nameFieldContainer,
    divisionFieldContainer,
    restFields,
    dateFieldsContainer,
    phoneFieldContainer,
    addressFieldContainer,
    apartmentFieldContainer,
    btnsContainer
  );

  return modalForm;
}

$.ajax({
  url: "/api/objects",
  method: "GET",
  contentType: "application/json",
})
  .done(function (data) {
    objectTable = new DataTable("#objectTable", {
      aaData: data,
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
      buttons: [
        {
          //add new-object button
          text: "Новый подопечный",
          className: "new-obj-btn",
          attr: {
            id: "addNewObject",
          },
          action: function () {
            modal.style.display = "flex";
            modalTitle.innerText = "Добавить подопечного";
            createForm();
            modalBody.appendChild(modalForm);

            let addressField = document.getElementById("addressField");
            addressField.addEventListener("input", addressType);

            document.getElementById("saveBtn").onclick = createObject;
          },
        },
      ],

      columns: [
        { data: "division_name" },
        { data: "name" },
        { data: "address" },
        { data: "apartment_number" },
        { data: "phone" },
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
    $("#objectTable").DataTable().draw();
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
  });

// When change button is clicked, create modal,
// fill form with api data
$("#objectTable").on("click", "button", function (e) {
  currentRowOfTable = e.target.closest("tr");
  let data = objectTable.row(e.target.closest("tr")).data();

  modal.style.display = "flex";
  modalTitle.innerText = `Изменить подопечного ${
    localStorage.getItem("rang-id") == 1 ? " ID: " + data.object_id : ""
  }`;
  modalForm = createForm();
  modalBody.appendChild(modalForm);

  let deleteAccess = localStorage.getItem("rang-id");
  if (deleteAccess == "1") {
    let deleteBtn = document.createElement("button");
    deleteBtn.id = "deleteBtn";
    deleteBtn.type = "button";
    deleteBtn.innerText = "Удалить";
    deleteBtn.onclick = deleteObject;

    document
      .getElementById("btnsContainer")
      .insertBefore(deleteBtn, document.getElementById("saveBtn"));
  }

  let name = document.getElementById("nameField");
  name.setAttribute("object-id", data.object_id);
  let options = document.getElementById("divisionField").childNodes;
  let noPayments = document.getElementById("noPaymentCheck");
  let active = document.getElementById("activeCheck");
  let phone = document.getElementById("phoneField");
  let address = document.getElementById("addressField");
  let startDate = document.getElementById("startDateField");
  let endDate = document.getElementById("endDateField");
  let apartment = document.getElementById("apartmentField");
  let saveBtn = document.getElementById("saveBtn");

  name.value = data.name;
  options.forEach((o) =>
    data.division_name === o.innerText ? (o.selected = true) : null
  );
  data.no_payments ? (noPayments.checked = true) : null;
  data.active ? (active.checked = true) : null;
  phone.value = data.phone;
  address.value = data.address;
  address.setAttribute("lat", data.latitude);
  address.setAttribute("lon", data.longitude);
  startDate.value = data.admission_date;
  endDate.value = data.denial_date;
  apartment.value = data.apartment_number;

  saveBtn.onclick = changeObject;
});

closeModal.addEventListener("click", hideModal);

function switchAddress() {
  let checkbox = document.getElementById("switchAddressBtn");
  if (!checkbox.checked) {
    localStorage.setItem("address-sorce", "2");
  } else if (checkbox.checked) {
    localStorage.setItem("address-sorce", "1");
  }
}

let lat;
let lon;

//create addresses container
let addressOuterContainer = document.createElement("div");
addressOuterContainer.id = "addressOuterContainer";
addressOuterContainer.style.display = "none";

let addressContainer = document.createElement("div");
addressContainer.id = "addressContainer";

addressOuterContainer.append(addressContainer);
modalForm.append(addressOuterContainer);

// when user clicks on the one of addresses
// get its value and append to input value,
// set attributes lat and lon
// then hide addresses container
function getOption(e) {
  let addressInput = document.getElementById("addressField");
  let selectedOp = document.getElementById(e.target.id);
  lat = selectedOp.getAttribute("lat");
  lon = selectedOp.getAttribute("lon");
  addressInput.value = selectedOp.innerText;
  addressInput.setAttribute("lat", lat);
  addressInput.setAttribute("lon", lon);
  addressOuterContainer.style.display = "none";
  addressContainer.innerHTML = "";
  lat = "";
  lon = "";
}

// looking address from api, when found, all match addresses
// show in list
// list shows under the input
function getAddressList() {
  let addressInput = document.getElementById("addressField");
  let adValue = addressInput.value;
  if (adValue == "") {
    addressOuterContainer.style.display = "none";
    addressContainer.innerHTML = "";
    return;
  }
  let url;

  url =
    localStorage.getItem("address-sorce") === "1"
      ? `api/address-lookup/google/${adValue}`
      : `api/address-lookup/${adValue}`;
  fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }

      return Promise.reject(response);
    })
    .then((data) => {
      let inputRect = addressInput.getBoundingClientRect();
      let left = inputRect.left;
      let bottom = inputRect.bottom;

      addressOuterContainer.style.left = left + "px";
      addressOuterContainer.style.top = bottom + "px";
      addressOuterContainer.style.display = "block";
      addressContainer.innerHTML = "";

      data.forEach((ad, index) => {
        if (adValue === ad.display_name) {
          return;
        }
        let op = document.createElement("div");
        op.className = "address-options";
        op.id = "address" + index;
        op.setAttribute("lat", ad.lat);
        op.setAttribute("lon", ad.lon);
        op.onclick = getOption;
        op.innerText = ad.display_name;

        addressContainer.append(op);
      });
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
    });
}

// listen of input address, reset timeout on sending address
// every time, when input value changes
let time;
function addressType() {
  let addressInput = document.getElementById("addressField");
  if (addressInput.hasAttribute("lat") && addressInput.hasAttribute("lon")) {
    addressInput.removeAttribute("lat");
    addressInput.removeAttribute("lon");
  }
  clearTimeout(time);
  time = setTimeout(getAddressList, 500);
}

// check and change addresses position
function addressesPosition() {
  let addressInput = document.getElementById("addressField");
  if (addressInput == null || addressInput == undefined) {
    return;
  }
  let inputRect = addressInput.getBoundingClientRect();
  let left = inputRect.left;
  let bottom = inputRect.bottom;
  if (addressInput.value == "") {
    return;
  }
  if (
    left == addressOuterContainer.style.left &&
    bottom == addressOuterContainer.style.top
  ) {
    return;
  }
  if (
    left != addressOuterContainer.style.left ||
    bottom != addressOuterContainer.style.top
  ) {
    addressOuterContainer.style.left = left + "px";
    addressOuterContainer.style.top = bottom + "px";
  }
}

window.addEventListener("resize", addressesPosition);

// collect new object fields data
function createObject() {
  let addressInput = document.getElementById("addressField");
  let name = document.getElementById("nameField").value;

  let options = document.getElementById("divisionField");
  let divisionId =
    options.options[options.selectedIndex].getAttribute("division_id");

  let startDate = document.getElementById("startDateField").value;
  let endDate = document.getElementById("endDateField").value;
  let latitude = addressInput.getAttribute("lat");
  let longitude = addressInput.getAttribute("lon");
  let address = addressInput.value;
  let apartment = document.getElementById("apartmentField").value;
  let noPayments = document.getElementById("noPaymentCheck").checked;
  let active = document.getElementById("activeCheck").checked;
  let phone = document.getElementById("phoneField").value;

  if (name == "" || longitude == null || latitude == null || address == "") {
    return;
  }

  let parameters = {
    name: name,
    division: divisionId,
    latitude: latitude,
    longitude: longitude,
    address: address,
  };

  startDate ? (parameters["admission_date"] = startDate) : null;
  endDate ? (parameters["denial_date"] = endDate) : null;

  noPayments ? (parameters["no_payments"] = noPayments) : null;
  active ? (parameters["active"] = active) : null;

  apartment != "" ? (parameters["apartment_number"] = apartment) : null;
  phone != "" ? (parameters["phone"] = phone) : null;

  console.log(parameters);
  sendNewObject(parameters);
}

// send new object data to api and get responses
function sendNewObject(parameters) {
  fetch("/api/objects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
      alertsToggle("Подопечный добавлен!", "success", 2500);
      $("#objectTable").DataTable().row.add(data).draw();
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
    });
}

// collect edit object fields data
function changeObject() {
  let addressInput = document.getElementById("addressField");
  let name = document.getElementById("nameField").value;

  let options = document.getElementById("divisionField");
  let divisionId =
    options.options[options.selectedIndex].getAttribute("division_id");

  let startDate = document.getElementById("startDateField").value;
  let endDate = document.getElementById("endDateField").value;
  let latitude = addressInput.getAttribute("lat");
  let longitude = addressInput.getAttribute("lon");
  let address = addressInput.value;
  let apartment = document.getElementById("apartmentField").value;
  let noPayments = document.getElementById("noPaymentCheck").checked;
  let active = document.getElementById("activeCheck").checked;
  let phone = document.getElementById("phoneField").value;

  if (name == "" || longitude == null || latitude == null || address == "") {
    return;
  }

  let parameters = {
    name: name,
    division: divisionId,
    admission_date: startDate == "" ? null : startDate,
    denial_date: endDate == "" ? null : endDate,
    latitude: latitude,
    longitude: longitude,
    address: address,
    no_payments: noPayments,
    active: active,
    phone: phone,
    apartment_number: apartment,
  };

  sendEditObject(parameters);
  console.log("parameters: ", parameters);
}

// send edit object data to api and get responses
function sendEditObject(parameters) {
  let objectId = document.getElementById("nameField").getAttribute("object-id");
  fetch(`/api/objects/${objectId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parameters),
  })
    .then((response) => {
      if (response.status === 200) {
        return response.json();
      }
      return Promise.reject(response);
    })
    .then((data) => {
      console.log(data);
      // let access = JSON.parse(localStorage.getItem("access"));
      // access.forEach((d) => {
      //   d.division_id === data.division
      //     ? (data["division_name"] = d.division)
      //     : null;
      // });
      // console.log("data with division-name ", data);
      hideModal();
      alertsToggle("Подопечный изменен!", "success", 2500);
      $("#objectTable").DataTable().row(currentRowOfTable).data(data).draw();
      currentRowOfTable = null;
    })
    .catch((response) => {
      if (response.status === 404) {
        alertsToggle("Подопечный не найден!", "danger", 3000);
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
      if (response.status === 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}

// send delete object object_id to api and get responses
// method not implemented yet
function deleteObject() {
  let objectId = document.getElementById("nameField").getAttribute("object-id");
  if (!confirm("Действительно хотите удалить подопечного?")) return;
  fetch(`/api/objects/${objectId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  })
    .then((response) => {
      if (response.status === 204) {
        hideModal();
        alertsToggle("Подопечный удален!", "success", 2500);
        $("#objectTable").DataTable().row(currentRowOfTable).remove().draw();
        currentRowOfTable = null;
      }
      return Promise.reject(response);
    })
    .catch((response) => {
      if (response.status === 403) {
        alertsToggle("Отказано в доступе!", "danger", 3000);
      }
      if (response.status === 404) {
        alertsToggle("Подопечный не найден!", "danger", 3000);
      }
      if (response.status === 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}
