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
