<template>
  <footer class="footer" id="contacts" role="contentinfo" aria-label="Подвал сайта">
    <div class="container">
      <div class="footer__inner">
        <div class="footer__column footer__column--brand">
          <div class="footer__brand" aria-label="Логотип платформы Тихая помощь">
            <span class="footer__brand-mark" aria-hidden="true">
              <img class="footer__brand-icon" src="/icons/logo-heart.svg" alt="" aria-hidden="true" />
            </span>
            <span class="footer__brand-text">Тихая помощь</span>
          </div>
          <p class="footer__description">
            Платформа прозрачной анонимной помощи нуждающимся
          </p>
        </div>

        <div class="footer__column">
          <h2 class="footer__title">Навигация</h2>
          <p class="footer__link">О платформе</p>
          <p class="footer__link">Помочь другому</p>
          <p class="footer__link">Получить помощь</p>
        </div>

        <div class="footer__column">
          <h2 class="footer__title">Поддержка</h2>
          <p class="footer__link">Частые вопросы</p>
          <p class="footer__link">Политика конфиденциальности</p>
          <p class="footer__link">Условия использования</p>
        </div>

        <div class="footer__column">
          <h2 class="footer__title">Контакты</h2>
          <p class="footer__link footer__link--icon">
            <img class="footer__contact-icon--image" src="/icons/mail.svg" alt="" aria-hidden="true" />
            <span>help@help.ru</span>
          </p>
          <p class="footer__link footer__link--icon">
            <img class="footer__contact-icon--image" src="/icons/phone.svg" alt="" aria-hidden="true" />
            <span>+7 (000) 000-00-00</span>
          </p>
          <p class="footer__link footer__link--icon">
            <img
              class="footer__contact-icon--image"
              src="/icons/map-pin.svg"
              alt=""
              aria-hidden="true"
            />
            <span>Сургут, Россия</span>
          </p>
        </div>
      </div>

      <div class="footer__bottom">
        <p class="footer__copyright">© 2026 Тихая помощь. Все права защищены.</p>
        <div class="footer__socials">
          <span class="footer__social">Telegram</span>
          <span class="footer__social">VK</span>
          <span class="footer__social">OK</span>
        </div>
      </div>
    </div>
  </footer>
</template>
