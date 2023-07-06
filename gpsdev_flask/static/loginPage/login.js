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

async function login() {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      phone: 79999774705,
      password: "testicles737",
    }),
  });
}
