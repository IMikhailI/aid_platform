<template>
  <section class="categories" id="categories" aria-labelledby="categories-title">
    <div class="container">
      <div class="section-heading">
        <h2 class="section-heading__title" id="categories-title">Категории помощи</h2>
        <p class="section-heading__text">
          Помогаем закрыть основные базовые потребности нуждающихся
        </p>
      </div>

      <div class="categories__grid">
        <article class="category-card category-card--food">
          <div class="category-card__icon" aria-hidden="true">
            <img class="category-card__icon-image" src="/icons/store.svg" alt="" aria-hidden="true" />
          </div>
          <h3 class="category-card__title">Еда</h3>
          <p class="category-card__text">Продуктовые наборы, сертификаты в магазины</p>
        </article>

        <article class="category-card category-card--kids">
          <div class="category-card__icon" aria-hidden="true">
            <img class="category-card__icon-image" src="/icons/baby-face.svg" alt="" aria-hidden="true" />
          </div>
          <h3 class="category-card__title">Детские товары</h3>
          <p class="category-card__text">Подгузники, питание, одежда, игрушки</p>
        </article>

        <article class="category-card category-card--medicine">
          <div class="category-card__icon" aria-hidden="true">
            <img class="category-card__icon-image" src="/icons/pill.svg" alt="" aria-hidden="true" />
          </div>
          <h3 class="category-card__title">Лекарства</h3>
          <p class="category-card__text">Оплата рецептов и счетов в аптеках</p>
        </article>

        <article class="category-card category-card--clothes">
          <div class="category-card__icon" aria-hidden="true">
            <img class="category-card__icon-image" src="/icons/shirt.svg" alt="" aria-hidden="true" />
          </div>
          <h3 class="category-card__title">Одежда</h3>
          <p class="category-card__text">Сезонная одежда и обувь для всей семьи</p>
        </article>
      </div>
    </div>
  </section>
</template>
