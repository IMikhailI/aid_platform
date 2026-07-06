<script setup>
import { authStore } from "../../stores/authStore";
</script>

<template>
  <section class="helper-page helper-settings">
    <header class="helper-page__heading">
      <h1>Настройки профиля</h1>
      <p>Управляйте своими личными данными и настройками</p>
    </header>

    <section class="helper-panel helper-settings-card">
      <h2>Личная информация</h2>
      <div class="helper-settings-grid">
        <label class="helper-readonly-field helper-readonly-field--wide"><span>Имя пользователя</span><input :value="authStore.currentUser.value?.username || ''" readonly /></label>
        <label class="helper-readonly-field"><span>Email</span><input :value="authStore.currentUser.value?.email || 'Не указан'" readonly /></label>
        <label class="helper-readonly-field"><span>Роль</span><input value="Помощник" readonly /></label>
        <label class="helper-readonly-field helper-readonly-field--wide"><span>Регион</span><input :value="authStore.currentUser.value?.region || 'Не указан'" readonly /></label>
      </div>
      <div class="helper-settings-note">Редактирование профиля будет доступно позже</div>
    </section>

    <section class="helper-panel helper-settings-card">
      <h2>Уведомления</h2>
      <div class="helper-setting-row"><div><strong>Email уведомления</strong><span>Получать уведомления на почту</span></div><button type="button" disabled>Будет доступно позже</button></div>
      <div class="helper-setting-row"><div><strong>Новые отклики</strong><span>Уведомления об изменениях ваших откликов</span></div><button type="button" disabled>Будет доступно позже</button></div>
    </section>

    <section class="helper-danger-card">
      <h2>Удаление аккаунта</h2>
      <p>Backend пока не поддерживает самостоятельное удаление аккаунта.</p>
      <button type="button" disabled>Удалить аккаунт</button>
    </section>
  </section>
</template>
