// checks if a value matches a pattern
function checkPattern(id) {
  let element = document.getElementById(id);
  let pattern = element.getAttribute("pattern");

  let re = new RegExp(pattern);

  return re.test(element.value);
}

export { checkPattern };
