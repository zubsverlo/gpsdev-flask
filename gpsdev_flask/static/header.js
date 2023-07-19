const menuBtn = document.getElementById("menuBtn");
const menuContainer = document.getElementById("openMenuContainer");

let shown = false;

menuBtn.addEventListener("click", togleMenu);

function togleMenu() {
  shown === false ? (shown = true) : (shown = false);
  if (shown === false) {
    menuContainer.style.maxHeight = "0";
  }
  if (shown === true) {
    menuContainer.style.maxHeight = "300px";
  }
}

function logOut() {
  fetch("api/auth/logout", { method: "POST" })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Выход не осуществлен. Попробуйте еще раз!");
      }
      location.href = "/login";
    })
    .catch((error) => console.log(error));
}
