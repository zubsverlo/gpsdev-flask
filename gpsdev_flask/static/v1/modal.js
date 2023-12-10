const modal = document.getElementById("modalContainer");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    hideModal();
  }
});

// clear and hide Modal
export function hideModal() {
  const closeEvent = new Event("modalClose");
  document.dispatchEvent(closeEvent);
  modal.style.display = "none";
  modalTitle.innerText = "";
  if (document.getElementById("modalForm")) {
    let modalForm = document.getElementById("modalForm");
    modalForm.innerHTML = "";
  }
  modalBody.innerHTML = "";
}
