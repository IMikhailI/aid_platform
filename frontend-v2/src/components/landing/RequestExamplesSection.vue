<script setup>
import { ref } from "vue";

const currentPage = ref(0);
const lastPage = 1;
</script>

<template>
  <section class="requests" id="requests" aria-labelledby="requests-title">
    <div class="container">
      <div class="section-heading">
        <h2 class="section-heading__title" id="requests-title">Примеры запросов о помощи</h2>
        <p class="section-heading__text">
          Реальные заявки нуждающихся на платформе
        </p>
      </div>

      <div class="requests__slider" data-carousel="requests">
        <button
          class="requests__arrow requests__arrow--prev"
          type="button"
          aria-label="Предыдущая страница запросов"
          :disabled="currentPage === 0"
          @click="currentPage -= 1"
        >
          &lt;
        </button>

        <div class="requests__viewport">
          <div class="requests__track" :style="{ transform: `translateX(-${currentPage * 100}%)` }">
            <div class="requests__page">
              <article class="request-card">
                <div class="request-card__top">
                  <p class="request-card__category">Еда</p>
                  <p class="request-card__city">Москва</p>
                </div>
                <h3 class="request-card__title">Продукты для семьи</h3>
                <p class="request-card__text">
                  Многодетная семья, 3 детей до 10 лет. Нужны продукты на месяц: крупы,
                  макароны, консервы.
                </p>
                <div class="request-card__meta">
                  <span>≈ 8 000 ₽</span>
                  <span>Проверено НКО</span>
                </div>
              </article>

              <article class="request-card">
                <div class="request-card__top">
                  <p class="request-card__category">Лекарства</p>
                  <p class="request-card__city">Тюмень</p>
                </div>
                <h3 class="request-card__title">Оплата курса терапии</h3>
                <p class="request-card__text">
                  Нужна оплата назначенных лекарств после выписки из стационара. Все рецепты
                  и документы уже подтверждены.
                </p>
                <div class="request-card__meta">
                  <span>≈ 5 300 ₽</span>
                  <span>Проверено НКО</span>
                </div>
              </article>

              <article class="request-card">
                <div class="request-card__top">
                  <p class="request-card__category">Детские товары</p>
                  <p class="request-card__city">Екатеринбург</p>
                </div>
                <h3 class="request-card__title">Одежда для малыша</h3>
                <p class="request-card__text">
                  Ребенок растет очень быстро, нужна зимняя одежда на 2 года: комбинезон,
                  ботинки и термобелье.
                </p>
                <div class="request-card__meta">
                  <span>≈ 6 000 ₽</span>
                  <span>Проверено НКО</span>
                </div>
              </article>
            </div>

            <div class="requests__page">
              <article class="request-card">
                <div class="request-card__top">
                  <p class="request-card__category">Одежда</p>
                  <p class="request-card__city">Сургут</p>
                </div>
                <h3 class="request-card__title">Тёплая одежда к зиме</h3>
                <p class="request-card__text">
                  Для одинокой мамы и двух детей нужно собрать зимний комплект одежды и обуви
                  до начала холодов.
                </p>
                <div class="request-card__meta">
                  <span>≈ 11 500 ₽</span>
                  <span>Проверено НКО</span>
                </div>
              </article>

              <article class="request-card">
                <div class="request-card__top">
                  <p class="request-card__category">Еда</p>
                  <p class="request-card__city">Пермь</p>
                </div>
                <h3 class="request-card__title">Сертификат в супермаркет</h3>
                <p class="request-card__text">
                  Семье нужен продуктовый сертификат, чтобы самостоятельно выбрать питание
                  для ребёнка с особыми ограничениями.
                </p>
                <div class="request-card__meta">
                  <span>≈ 7 000 ₽</span>
                  <span>Проверено НКО</span>
                </div>
              </article>

              <article class="request-card">
                <div class="request-card__top">
                  <p class="request-card__category">Гигиена</p>
                  <p class="request-card__city">Казань</p>
                </div>
                <h3 class="request-card__title">Набор первой необходимости</h3>
                <p class="request-card__text">
                  Для кризисного центра требуется набор бытовой химии, средств гигиены и
                  подгузников для новоприбывшей семьи.
                </p>
                <div class="request-card__meta">
                  <span>≈ 4 200 ₽</span>
                  <span>Проверено НКО</span>
                </div>
              </article>
            </div>
          </div>
        </div>

        <button
          class="requests__arrow requests__arrow--next"
          type="button"
          aria-label="Следующая страница запросов"
          :disabled="currentPage === lastPage"
          @click="currentPage += 1"
        >
          &gt;
        </button>
      </div>

      <div class="requests__dots" role="group" aria-label="Страницы карусели запросов">
        <button
          class="requests__dot"
          :class="{ 'requests__dot--active': currentPage === 0 }"
          type="button"
          aria-label="Показать первую страницу запросов"
          :aria-current="currentPage === 0"
          @click="currentPage = 0"
        ></button>
        <button
          class="requests__dot"
          :class="{ 'requests__dot--active': currentPage === 1 }"
          type="button"
          aria-label="Показать вторую страницу запросов"
          :aria-current="currentPage === 1"
          @click="currentPage = 1"
        ></button>
      </div>
    </div>
  </section>
</template>
