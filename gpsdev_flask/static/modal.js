const modal = document.getElementById("modalContainer");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");

// clear and hide Modal
export function hideModal() {
  modal.style.display = "none";
  modalTitle.innerText = "";
  if (document.getElementById("modalForm")) {
    let modalForm = document.getElementById("modalForm");
    modalForm.innerHTML = "";
  }
  modalBody.innerHTML = "";
}
