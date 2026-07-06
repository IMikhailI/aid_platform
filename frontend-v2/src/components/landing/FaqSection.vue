<script setup>
import { ref } from "vue";

const openItem = ref(null);
const items = [
  {
    question: "Как гарантируется анонимность нуждающихся?",
    answer: "Данные заявителей проверяются партнёрскими НКО, а публично отображается только информация, необходимая для оказания помощи.",
  },
  {
    question: "Почему нет прямых денежных переводов?",
    answer: "Платформа работает через целевые платежи, чтобы снизить риск мошенничества и подтвердить, что помощь ушла по назначению.",
  },
  {
    question: "Кто проверяет заявки на платформе?",
    answer: "Заявки проходят модерацию через партнёрские НКО, фонды и социальные службы.",
  },
  {
    question: "Можно ли выбрать конкретного человека для помощи?",
    answer: "Обычно помощь оказывается по проверенным запросам, а персональные данные нуждающихся скрываются ради безопасности и конфиденциальности.",
  },
  {
    question: "Какие документы нужны для создания заявки?",
    answer: "Точный список подтверждающих документов зависит от категории запроса и требований партнёрской организации.",
  },
  {
    question: "Есть ли лимиты на сумму помощи?",
    answer: "Да, существуют разумные лимиты по суммам и частоте запросов для каждого пользователя.",
  },
];

function toggleItem(index) {
  openItem.value = openItem.value === index ? null : index;
}
</script>

<template>
  <section class="faq" id="faq" aria-labelledby="faq-title">
    <div class="container">
      <div class="section-heading">
        <h2 class="section-heading__title" id="faq-title">Частые вопросы</h2>
        <p class="section-heading__text">
          Ответы на популярные вопросы о работе платформы
        </p>
      </div>

      <div class="faq__list">
        <article v-for="(item, index) in items" :key="item.question" class="faq-item">
          <button
            class="faq-item__trigger"
            :id="`faq-trigger-${index + 1}`"
            type="button"
            :aria-expanded="openItem === index"
            :aria-controls="`faq-answer-${index + 1}`"
            @click="toggleItem(index)"
          >
            <span class="faq-item__question">{{ item.question }}</span>
            <img class="faq-item__icon" src="/icons/chevron-right.svg" alt="" aria-hidden="true" />
          </button>
          <div
            v-show="openItem === index"
            class="faq-item__panel"
            :id="`faq-answer-${index + 1}`"
            role="region"
            :aria-labelledby="`faq-trigger-${index + 1}`"
          >
            {{ item.answer }}
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
