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
