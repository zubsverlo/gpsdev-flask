export function alertsToggle(text, className, time = 2500) {
  // new alertContainer
  let newContainer = document.createElement("div");
  newContainer.id = "alertContainer";
  newContainer.className = "alert-container";
  newContainer.style =
    "position: fixed; z-index: 999; bottom: 30px; right: 10px; flex-direction: column;";
  // get alertContainer if it exist
  let alertContainer = document.getElementById("alertContainer");

  // if the container is not found, add a new container to the body
  if (!alertContainer) {
    alertContainer = newContainer;
    document.body.append(alertContainer);
  }
  let newAlert = document.createElement("div");
  let newAlertText = document.createElement("div");

  alertContainer.className = "alert-container";
  newAlert.className = `alert-message ${className} fade-in`;
  newAlert.id = "alertMessage";
  newAlertText.innerText = text;

  if (className === "warning" || className === "danger") {
    newAlert.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" class="svg-size" id="exclamation-triangle-fill" viewBox="0 0 16 16"><path d="M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/></svg>';
  } else if (className === "info") {
    newAlert.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" class="svg-size" id="info-fill" viewBox="0 0 16 16"><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/></svg>';
  } else if (className === "success") {
    newAlert.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" class="svg-size" id="check-circle-fill" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg>';
  }

  newAlert.append(newAlertText);
  alertContainer.append(newAlert);
  alertContainer.style.display = "flex";
  setTimeout(() => {
    alertContainer = document.getElementById("alertContainer");
    newAlert.className = `alert-message ${className} fade-out`;
    alertContainer.className = "alert-container ";
    setTimeout(() => {
      alertContainer = document.getElementById("alertContainer");
      let alertMessage = document.getElementById("alertMessage");
      alertMessage.style.display = "none";
      alertMessage.remove();
    }, 2500);
  }, time);
}

let offlineError;
window.addEventListener("offline", () => {
  offlineError = setInterval(() => {
    alertsToggle("Отсутствует интернет соединение!", "danger", 4000);
  }, 5000);
});

window.addEventListener("online", () => {
  clearInterval(offlineError);
  alertsToggle("Интернет соединение востановлено!", "success", 5000);
});
