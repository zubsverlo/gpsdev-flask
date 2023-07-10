const eyeBtn = document.getElementById("hideShow");

eyeBtn.addEventListener("click", () => {
  const passField = document.getElementById("password");
  if (passField.type === "password") {
    eyeBtn.src = "/static/loginPage/hide.png";
    passField.type = "text";
  } else {
    eyeBtn.src = "/static/loginPage/show.png";
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

async function login(e) {
  let pswd = document.getElementById("password").value;
  let phone = document.getElementById("pNumber").value;
  let credentials = { password: pswd, phone: phone };

  fetch("api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  })
    .then((response) => {
      if (response.status == 422) {
        throw new Error("Неверный логин или пароль!");
      }
      if (response.ok) {
        location.search
          ? (location.href = location.search.split("?next=")[1])
          : (location.href = "/home");
      }
      response.json;
    })
    .catch((error) => {
      const container = document.getElementById("errorContainer");
      container.innerText = "Неверный логин или пароль!";
      container.style.display = "flex";
    });
}
