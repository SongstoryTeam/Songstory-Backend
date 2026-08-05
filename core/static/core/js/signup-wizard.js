(() => {
  const wizard = document.querySelector('[data-wizard]');
  if (!wizard) return;

  const form = wizard.querySelector('[data-wizard-form]');
  const steps = Array.from(wizard.querySelectorAll('[data-wizard-step]'));
  const progressSteps = Array.from(wizard.querySelectorAll('[data-progress-step]'));
  const backBtn = wizard.querySelector('[data-wizard-back]');
  const nextBtn = wizard.querySelector('[data-wizard-next]');
  const submitBtn = wizard.querySelector('[data-wizard-submit]');

  if (!form || !backBtn || !nextBtn || !submitBtn || steps.length < 2) return;

  wizard.classList.add('wizard-js');

  let current = 0;
  const checkTimers = new WeakMap();
  const checkUrl = wizard.dataset.checkUrl;

  function fieldsOf(step) {
    return Array.from(step.querySelectorAll('input, select, textarea')).filter((el) => el.name);
  }

  function isStepValid(step) {
    return fieldsOf(step).every((el) => el.checkValidity());
  }

  function revealErrors(step) {
    fieldsOf(step).some((el) => {
      if (el.checkValidity()) return false;
      el.reportValidity();
      return true;
    });
  }

  function announce(message) {
    let live = wizard.querySelector('[data-wizard-live]');
    if (!live) {
      live = document.createElement('div');
      live.setAttribute('data-wizard-live', '');
      live.setAttribute('aria-live', 'polite');
      live.className = 'visually-hidden';
      wizard.appendChild(live);
    }
    live.textContent = message;
  }

  function goToStep(index) {
    steps.forEach((step, i) => step.toggleAttribute('data-wizard-hidden', i !== index));
    progressSteps.forEach((item, i) => {
      item.classList.toggle('is-active', i === index);
      item.classList.toggle('is-done', i < index);
    });

    backBtn.toggleAttribute('data-wizard-hidden', index === 0);
    nextBtn.toggleAttribute('data-wizard-hidden', index === steps.length - 1);
    submitBtn.toggleAttribute('data-wizard-hidden', index !== steps.length - 1);

    current = index;

    const firstField = steps[index].querySelector('input, select, textarea');
    if (firstField) firstField.focus({ preventScroll: true });

    announce(`Крок ${index + 1} з ${steps.length}`);
  }

  function goNext() {
    const step = steps[current];
    if (!isStepValid(step)) {
      revealErrors(step);
      return;
    }
    if (current < steps.length - 1) goToStep(current + 1);
  }

  function goBack() {
    if (current > 0) goToStep(current - 1);
  }

  backBtn.addEventListener('click', goBack);
  nextBtn.addEventListener('click', goNext);

  form.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.target.tagName === 'TEXTAREA') return;
    if (current !== steps.length - 1) {
      event.preventDefault();
      goNext();
    }
  });

  progressSteps.forEach((item, index) => {
    item.addEventListener('click', () => {
      if (index === current) return;
      if (index < current) {
        goToStep(index);
        return;
      }
      for (let i = current; i < index; i += 1) {
        if (!isStepValid(steps[i])) {
          revealErrors(steps[i]);
          return;
        }
      }
      goToStep(index);
    });
  });

  form.addEventListener('submit', (event) => {
    const firstInvalidStep = steps.findIndex((step) => !isStepValid(step));
    if (firstInvalidStep === -1) return;
    event.preventDefault();
    goToStep(firstInvalidStep);
    revealErrors(steps[firstInvalidStep]);
  });

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

      checkTimers.set(input, window.setTimeout(() => checkAvailability(input, feedback), 400));
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
      strengthBar.style.width = `${(score / 4) * 100}%`;
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

  goToStep(0);
})();
