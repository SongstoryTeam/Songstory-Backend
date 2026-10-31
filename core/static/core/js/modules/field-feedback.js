window.Songstery = window.Songstery || {};

window.Songstery.createFieldFeedback = (node, messages) => {
    const BASE_CLASS = 'field-feedback';
    const MODIFIERS = Object.freeze({pending: 'pending', ok: 'ok', invalid: 'error', broken: 'error'});

    function show(state) {
        const modifier = MODIFIERS[state];
        node.textContent = messages[state] ?? '';
        node.className = modifier ? `${BASE_CLASS} ${BASE_CLASS}--${modifier}` : BASE_CLASS;
    }

    return {show};
};
