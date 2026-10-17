window.Songstery = window.Songstery || {};

/**
 * Рушій покрокової форми: прогрес, навігація, перевірка валідності кроків і клавіатура.
 * Розмітка відповідає за вміст кроків, а специфічну поведінку сторінки підключають хуки:
 * beforeLeave(index, step) -> Promise<boolean> може зупинити перехід далі, onEnter(index, step) викликається після переходу.
 * Без JS усі кроки показані одним списком, а сервер перевіряє форму повністю.
 */
window.Songstery.createWizard = (root, hooks = {}) => {
    const STEP_ANNOUNCEMENT = (index, total) => `Крок ${index + 1} з ${total}`;
    const FIELD_SELECTOR = 'input, select, textarea';

    const form = root.querySelector('[data-wizard-form]');
    const steps = Array.from(root.querySelectorAll('[data-wizard-step]'));
    const progressSteps = Array.from(root.querySelectorAll('[data-progress-step]'));
    const backButton = root.querySelector('[data-wizard-back]');
    const nextButton = root.querySelector('[data-wizard-next]');
    const submitButton = root.querySelector('[data-wizard-submit]');

    if (!form || !backButton || !nextButton || !submitButton || steps.length < 2) return null;

    const beforeLeave = hooks.beforeLeave || (async () => true);
    const onEnter = hooks.onEnter || (() => {});

    let current = 0;
    let transitioning = false;

    root.classList.add('wizard-js');

    const fieldsOf = (step) => Array.from(step.querySelectorAll(FIELD_SELECTOR)).filter((field) => field.name);
    const isStepValid = (step) => fieldsOf(step).every((field) => field.checkValidity());

    function revealErrors(step) {
        fieldsOf(step).some((field) => {
            if (field.checkValidity()) return false;
            field.reportValidity();
            return true;
        });
    }

    function announce(message) {
        let live = root.querySelector('[data-wizard-live]');
        if (!live) {
            live = document.createElement('div');
            live.setAttribute('data-wizard-live', '');
            live.setAttribute('aria-live', 'polite');
            live.className = 'visually-hidden';
            root.appendChild(live);
        }
        live.textContent = message;
    }

    function setBusy(busy) {
        transitioning = busy;
        nextButton.disabled = busy;
        root.toggleAttribute('aria-busy', busy);
    }

    function goTo(index) {
        steps.forEach((step, position) => step.toggleAttribute('data-wizard-hidden', position !== index));
        progressSteps.forEach((item, position) => {
            item.classList.toggle('is-active', position === index);
            item.classList.toggle('is-done', position < index);
            if (position === index) item.setAttribute('aria-current', 'step');
            else item.removeAttribute('aria-current');
        });

        backButton.toggleAttribute('data-wizard-hidden', index === 0);
        nextButton.toggleAttribute('data-wizard-hidden', index === steps.length - 1);
        submitButton.toggleAttribute('data-wizard-hidden', index !== steps.length - 1);

        current = index;
        steps[index].querySelector(FIELD_SELECTOR)?.focus({preventScroll: true});
        announce(STEP_ANNOUNCEMENT(index, steps.length));
        onEnter(index, steps[index]);
    }

    async function blockerAt(index) {
        if (!isStepValid(steps[index])) return 'invalid';
        return (await beforeLeave(index, steps[index])) ? null : 'rejected';
    }

    async function advanceTo(target) {
        if (transitioning || target <= current) return;
        setBusy(true);
        try {
            for (let index = current; index < target; index += 1) {
                const blocker = await blockerAt(index);
                if (!blocker) continue;
                if (index !== current) goTo(index);
                if (blocker === 'invalid') revealErrors(steps[index]);
                return;
            }
            goTo(target);
        } finally {
            setBusy(false);
        }
    }

    const goNext = () => advanceTo(current + 1);
    const goBack = () => {
        if (current > 0) goTo(current - 1);
    };

    backButton.addEventListener('click', goBack);
    nextButton.addEventListener('click', goNext);

    form.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' || !(event.target instanceof HTMLInputElement) || current === steps.length - 1) return;
        event.preventDefault();
        goNext();
    });

    progressSteps.forEach((item, index) => {
        item.addEventListener('click', () => {
            if (index < current) goTo(index);
            else advanceTo(index);
        });
    });

    form.addEventListener('submit', (event) => {
        const invalidIndex = steps.findIndex((step) => !isStepValid(step));
        if (invalidIndex === -1) return;
        event.preventDefault();
        goTo(invalidIndex);
        revealErrors(steps[invalidIndex]);
    });

    const stepWithServerError = steps.findIndex((step) => step.querySelector('[data-wizard-error]'));
    goTo(Math.max(stepWithServerError, 0));

    return {goTo, goNext, goBack, steps, get current() { return current; }};
};
