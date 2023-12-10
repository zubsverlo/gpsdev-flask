import { alertsToggle } from "../../../v1/alerts.js";
import { checkPattern } from "../../../v1/check_pattern.js";

const eyeBtn = document.getElementById("hideShow");

eyeBtn.addEventListener("click", () => {
  const passField = document.getElementById("password");
  if (passField.type === "password") {
    eyeBtn.src = "/static/v1/icons/hide.png";
    passField.type = "text";
  } else {
    eyeBtn.src = "/static/v1/icons/show.png";
    passField.type = "password";
  }
});

const loginBtn = document.getElementById("loginBtn");

loginBtn.addEventListener("mouseover", () => {
  let bgImage = document.getElementById("bgImage");
  bgImage.style.backgroundSize = "100%";
});

loginBtn.addEventListener("mouseout", () => {
  let bgImage = document.getElementById("bgImage");
  bgImage.style.backgroundSize = "150%";
});

loginBtn.addEventListener("click", login);

function login(e) {
  let pswd = document.getElementById("password").value;
  let phone = document.getElementById("pNumber").value;
  if (pswd == "" || phone == "") {
    return;
  }
  if (!checkPattern("pNumber")) {
    return alertsToggle("Введите номер в формате: 79991231122", "danger", 3000);
  }
  let credentials = { password: pswd, phone: phone };

  fetch("api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      }
      return Promise.reject(response);
    })
    .then((data) => {
      let access = JSON.stringify(data.access);

      localStorage.setItem("access", access);
      localStorage.setItem("id", data.id);
      localStorage.setItem("name", data.name);
      localStorage.setItem("phone", data.phone);
      localStorage.setItem("rang", data.rang);
      localStorage.setItem("rang-id", data.rang_id);

      location.search
        ? (location.href = location.search.split("?next=")[1])
        : (location.href = "/");
    })
    .catch((response) => {
      if (response.status == 422) {
        response.json().then((error) => {
          alertsToggle("Неверный логин или пароль!", "danger", 3000);
        });
      }
      if (json.status == 500) {
        alertsToggle(
          "Ошибка сервера! Повторите попытку, или свяжитесь с администратором.",
          "danger",
          6000
        );
      }
    });
}
