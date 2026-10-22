(() => {
  const AVAILABILITY_DEBOUNCE_MS = 400;
  const MAX_PASSWORD_SCORE = 4;
  const PERCENT = 100;

  const wizard = document.querySelector('[data-wizard]');
  const {createWizard} = window.Songstery || {};
  if (!wizard || !createWizard || !createWizard(wizard)) return;

  const checkTimers = new WeakMap();
  const checkUrl = wizard.dataset.checkUrl;

  async function checkAvailability(input, feedback) {
    if (!checkUrl) return;
    feedback.textContent = 'Перевіряємо…';
    feedback.className = 'field-feedback field-feedback--pending';

    try {
      const params = new URLSearchParams({ field: input.dataset.check, value: input.value });
      const response = await fetch(`${checkUrl}?${params.toString()}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!response.ok) throw new Error('Availability check failed');
      const data = await response.json();

      if (data.available === true) {
        feedback.textContent = 'Вільно';
        feedback.className = 'field-feedback field-feedback--ok';
        input.setCustomValidity('');
      } else if (data.available === false) {
        const message = input.dataset.check === 'email'
          ? 'Ця пошта вже зареєстрована'
          : "Це ім'я вже зайняте";
        feedback.textContent = message;
        feedback.className = 'field-feedback field-feedback--error';
        input.setCustomValidity(message);
      } else {
        feedback.textContent = '';
        feedback.className = 'field-feedback';
        input.setCustomValidity('');
      }
    } catch (error) {
      feedback.textContent = '';
      feedback.className = 'field-feedback';
    }
  }

  wizard.querySelectorAll('[data-check]').forEach((input) => {
    const feedback = input.closest('.form-group').querySelector('[data-field-feedback]');
    if (!feedback) return;

    input.addEventListener('input', () => {
      input.setCustomValidity('');
      feedback.textContent = '';
      feedback.className = 'field-feedback';

      window.clearTimeout(checkTimers.get(input));
      if (!input.value || !input.checkValidity()) return;

      checkTimers.set(input, window.setTimeout(() => checkAvailability(input, feedback), AVAILABILITY_DEBOUNCE_MS));
    });
  });

  const passwordInput = wizard.querySelector('[data-role="password"]');
  const confirmInput = wizard.querySelector('[data-role="password-confirm"]');
  const strengthBar = wizard.querySelector('.password-strength__bar span');
  const strengthLabel = wizard.querySelector('.password-strength__label');
  const strengthLabels = ['Занадто слабкий', 'Слабкий', 'Прийнятний', 'Хороший', 'Надійний'];

  function scorePassword(value) {
    if (!value) return 0;
    let score = 0;
    if (value.length >= 8) score += 1;
    if (value.length >= 12) score += 1;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
    if (/\d/.test(value)) score += 1;
    if (/[^a-zA-Z0-9]/.test(value)) score += 1;
    return Math.min(score, 4);
  }

  function syncPasswordMatch() {
    if (!confirmInput.value) {
      confirmInput.setCustomValidity('');
      return;
    }
    confirmInput.setCustomValidity(
      confirmInput.value === passwordInput.value ? '' : 'Паролі не співпадають',
    );
  }

  if (passwordInput && strengthBar && strengthLabel) {
    passwordInput.addEventListener('input', () => {
      const score = scorePassword(passwordInput.value);
      strengthBar.style.width = `${(score / MAX_PASSWORD_SCORE) * PERCENT}%`;
      strengthBar.dataset.level = String(score);
      strengthLabel.textContent = passwordInput.value ? strengthLabels[score] : '';
    });
  }

  if (passwordInput && confirmInput) {
    passwordInput.addEventListener('input', syncPasswordMatch);
    confirmInput.addEventListener('input', syncPasswordMatch);
  }

  wizard.querySelectorAll('[data-password-toggle]').forEach((toggle) => {
    toggle.addEventListener('click', () => {
      const input = toggle.closest('.password-field').querySelector('input');
      const willShow = input.type === 'password';
      input.type = willShow ? 'text' : 'password';
      toggle.classList.toggle('is-visible', willShow);
      toggle.setAttribute('aria-label', willShow ? 'Приховати пароль' : 'Показати пароль');
    });
  });
})();
