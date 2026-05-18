const downloadButtons = document.querySelectorAll(".download-button");
let toastTimer;

const showToast = (message) => {
  let toast = document.querySelector(".toast");

  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.add("show");

  if (toastTimer) {
    window.clearTimeout(toastTimer);
  }

  toastTimer = window.setTimeout(() => {
    toast.classList.remove("show");
  }, 3200);
};

downloadButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showToast("O ficheiro APK ainda não foi adicionado ao site.");
  });
});

const carousel = document.querySelector(".hero-carousel");

if (carousel) {
  const images = Array.from(carousel.querySelectorAll(".carousel-image"));
  const prevButton = carousel.querySelector(".carousel-btn.prev");
  const nextButton = carousel.querySelector(".carousel-btn.next");
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (images.length > 1) {
    let currentIndex = images.findIndex((image) => image.classList.contains("active"));
    let autoTimer;

    if (currentIndex < 0) {
      currentIndex = 0;
      images[0].classList.add("active");
    }

    const setActive = (newIndex) => {
      images[currentIndex].classList.remove("active");
      currentIndex = (newIndex + images.length) % images.length;
      images[currentIndex].classList.add("active");
    };

    const showNext = () => setActive(currentIndex + 1);
    const showPrev = () => setActive(currentIndex - 1);

    prevButton?.addEventListener("click", showPrev);
    nextButton?.addEventListener("click", showNext);

    const startAuto = () => {
      if (prefersReducedMotion) {
        return;
      }

      if (autoTimer) {
        return;
      }

      autoTimer = window.setInterval(showNext, 6000);
    };

    const stopAuto = () => {
      if (!autoTimer) {
        return;
      }

      window.clearInterval(autoTimer);
      autoTimer = undefined;
    };

    startAuto();
    carousel.addEventListener("mouseenter", stopAuto);
    carousel.addEventListener("mouseleave", startAuto);
    carousel.addEventListener("focusin", stopAuto);
    carousel.addEventListener("focusout", startAuto);
  }
}
