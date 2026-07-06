const faqTriggers = document.querySelectorAll(".faq-item__trigger");

const setFaqState = (trigger, expanded) => {
  const panelId = trigger.getAttribute("aria-controls");
  const panel = panelId ? document.getElementById(panelId) : null;

  trigger.setAttribute("aria-expanded", String(expanded));

  if (panel) {
    panel.hidden = !expanded;
  }
};

faqTriggers.forEach((trigger) => {
  setFaqState(trigger, false);

  trigger.addEventListener("click", () => {
    const isExpanded = trigger.getAttribute("aria-expanded") === "true";

    faqTriggers.forEach((item) => setFaqState(item, false));
    setFaqState(trigger, !isExpanded);
  });
});

const carousels = document.querySelectorAll("[data-carousel]");

carousels.forEach((carousel) => {
  const track = carousel.querySelector(".requests__track");
  const prevButton = carousel.querySelector(".requests__arrow--prev");
  const nextButton = carousel.querySelector(".requests__arrow--next");
  const dots = carousel.parentElement?.querySelectorAll(".requests__dot");

  if (!track || !prevButton || !nextButton || !dots?.length) {
    return;
  }

  let currentIndex = 0;
  const lastIndex = dots.length - 1;

  const updateCarousel = () => {
    track.style.transform = `translateX(-${currentIndex * 100}%)`;

    prevButton.disabled = currentIndex === 0;
    nextButton.disabled = currentIndex === lastIndex;

    dots.forEach((dot, index) => {
      const isActive = index === currentIndex;
      dot.classList.toggle("requests__dot--active", isActive);
      dot.setAttribute("aria-current", String(isActive));
    });
  };

  prevButton.addEventListener("click", () => {
    if (currentIndex > 0) {
      currentIndex -= 1;
      updateCarousel();
    }
  });

  nextButton.addEventListener("click", () => {
    if (currentIndex < lastIndex) {
      currentIndex += 1;
      updateCarousel();
    }
  });

  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => {
      currentIndex = index;
      updateCarousel();
    });
  });

  updateCarousel();
});
