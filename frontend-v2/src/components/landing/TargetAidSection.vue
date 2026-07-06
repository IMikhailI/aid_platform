<template>
  <section class="cta" id="support" aria-labelledby="cta-title">
    <div class="container cta__inner">
      <div>
        <h2 class="cta__title" id="cta-title">Начните помогать уже сегодня</h2>
        <p class="cta__text">
          Каждая помощь важна. Выберите запрос и измените чью-то жизнь к
          лучшему
        </p>
      </div>

      <div class="cta__actions">
        <RouterLink
          class="cta__button cta__button--secondary"
          to="/login"
          aria-label="Получить помощь"
        >
          <img
            class="cta__button-icon cta__button-icon--light"
            src="/icons/logo-heart.svg"
            alt=""
            aria-hidden="true"
          />
          Получить помощь
        </RouterLink>
        <RouterLink
          class="cta__button cta__button--primary"
          to="/login"
          aria-label="Помочь другим"
        >
          Помочь другим
          <img
            class="cta__button-icon"
            src="/icons/arrow-right.svg"
            alt=""
            aria-hidden="true"
          />
        </RouterLink>
      </div>
    </div>
  </section>

  <section class="payments" aria-labelledby="payments-title">
    <div class="container payments__grid">
      <div class="payments__content">
        <div class="section-heading section-heading--left">
          <h2 class="section-heading__title" id="payments-title">
            Как работают целевые платежи
          </h2>
          <p class="section-heading__text">
            Никаких денежных переводов на карту — только прозрачная целевая
            помощь. Мы гарантируем, что средства пойдут именно на заявленные
            нужды через проверенных партнёров.
          </p>
        </div>
      </div>

      <div class="payments__cards">
        <article class="payment-card">
          <div class="payment-card__icon" aria-hidden="true">
            <img class="payment-card__icon-image" src="/icons/store.svg" alt="" aria-hidden="true" />
          </div>
          <div class="payment-card__body">
            <h3 class="payment-card__title">Сертификаты в магазины</h3>
            <p class="payment-card__text">
              Выдаем именные сертификаты на определенную сумму в партнерские
              супермаркеты. Человек сам выбирает нужные товары.
            </p>
          </div>
        </article>

        <article class="payment-card">
          <div class="payment-card__icon" aria-hidden="true">
            <img class="payment-card__icon-image" src="/icons/package-box.svg" alt="" aria-hidden="true" />
          </div>
          <div class="payment-card__body">
            <h3 class="payment-card__title">Прямая оплата в магазине</h3>
            <p class="payment-card__text">
              Благотворитель оплачивает конкретный список товаров через
              партнерский магазин. Нуждающийся забирает готовый заказ.
            </p>
          </div>
        </article>

        <article class="payment-card">
          <div class="payment-card__icon" aria-hidden="true">
            <img class="payment-card__icon-image" src="/icons/file-text.svg" alt="" aria-hidden="true" />
          </div>
          <div class="payment-card__body">
            <h3 class="payment-card__title">Оплата счетов и рецептов</h3>
            <p class="payment-card__text">
              Для лекарств оплачиваем счета в аптеках по рецепту врача. Для
              услуг — прямая оплата поставщику от лица благотворителя.
            </p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
