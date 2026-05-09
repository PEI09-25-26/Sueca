const downloadButtons = document.querySelectorAll(".download-button");

downloadButtons.forEach((button) => {
  button.addEventListener("click", () => {
    alert("O ficheiro APK ainda não foi adicionado ao site.");
  });
});
