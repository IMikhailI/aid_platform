<template>
  <section class="hero" id="hero" aria-labelledby="hero-title">
    <div class="container hero__container">
      <div class="hero__content">
        <p class="hero__eyebrow">Анонимная адресная помощь</p>
        <h1 class="hero__title" id="hero-title">Платформа прозрачной помощи нуждающимся</h1>
        <p class="hero__text">
          Объединяем людей в сложной ситуации с благотворителями через
          проверенных партнёров — НКО, фонды и социальные службы
        </p>

        <div class="hero__actions">
          <RouterLink
            class="hero__button hero__button--primary"
            to="/login"
            aria-label="Получить помощь"
          >
            <img
              class="hero__button-icon hero__button-icon--light"
              src="/icons/logo-heart.svg"
              alt=""
              aria-hidden="true"
            />
            Получить помощь
          </RouterLink>
          <RouterLink
            class="hero__button hero__button--secondary"
            to="/login"
            aria-label="Помочь другим"
          >
            Помочь другим
            <img
              class="hero__button-icon"
              src="/icons/arrow-right.svg"
              alt=""
              aria-hidden="true"
            />
          </RouterLink>
        </div>
      </div>

      <aside class="hero__aside" aria-label="Боковая карточка со статистикой платформы">
        <div
          class="hero-card"
          role="group"
          aria-label="Статистика платформы, оказано помощи 1.2 миллиона рублей"
        >
          <div class="hero-card__top">
            <h2 class="hero-card__title">Статистика платформы</h2>
            <div class="hero-card__live">
              <span class="hero-card__live-dot" aria-hidden="true"></span>
              <span>LIVE</span>
            </div>
          </div>

          <div class="hero-card__tabs" role="group" aria-label="Период статистики">
            <button class="hero-card__tab" type="button" aria-pressed="false">Неделя</button>
            <button class="hero-card__tab" type="button" aria-pressed="false">Месяц</button>
            <button
              class="hero-card__tab hero-card__tab--active"
              type="button"
              aria-pressed="true"
            >
              Всё время
            </button>
          </div>

          <p class="hero-card__label">Оказано помощи</p>
          <p class="hero-card__amount">1.2M ₽</p>

          <div class="hero-card__chart">
            <img
              class="hero-card__chart-image"
              src="/icons/graf.svg"
              alt="График оказанной помощи с января по июнь: рост до мая и снижение в июне"
            />
          </div>
        </div>
      </aside>
    </div>

    <div class="container">
      <div class="metrics">
        <article class="metrics__item">
          <h2 class="metrics__value">2,847</h2>
          <p class="metrics__label">Выполненных заявок</p>
        </article>
        <article class="metrics__item">
          <h2 class="metrics__value">1.2M ₽</h2>
          <p class="metrics__label">Оказано помощи</p>
        </article>
        <article class="metrics__item">
          <h2 class="metrics__value">127</h2>
          <p class="metrics__label">Партнёров</p>
        </article>
        <article class="metrics__item">
          <h2 class="metrics__value">93%</h2>
          <p class="metrics__label">Довольных пользователей</p>
        </article>
      </div>
    </div>
  </section>
</template>
