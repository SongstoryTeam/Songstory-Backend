window.Songstery = window.Songstery || {};

window.Songstery.createCoverChecker = ({delay, onState}) => {
    const STATES = Object.freeze({
        EMPTY: 'empty',
        INVALID: 'invalid',
        PENDING: 'pending',
        OK: 'ok',
        BROKEN: 'broken',
    });

    let timer = null;
    let generation = 0;

    function secureUrl(value) {
        try {
            const url = new URL(value);
            if (url.protocol === 'http:') url.protocol = 'https:';
            return url.protocol === 'https:' ? url.href : '';
        } catch {
            return '';
        }
    }

    function loads(url) {
        return new Promise((resolve) => {
            const image = new Image();
            image.addEventListener('load', () => resolve(image), {once: true});
            image.addEventListener('error', () => resolve(null), {once: true});
            image.src = url;
        });
    }

    async function check(raw) {
        generation += 1;
        const current = generation;
        const value = raw.trim();

        if (!value) return onState(STATES.EMPTY, '');
        const url = secureUrl(value);
        if (!url) return onState(STATES.INVALID, '');

        onState(STATES.PENDING, '');
        const image = await loads(url);
        if (current !== generation) return undefined;
        return onState(image ? STATES.OK : STATES.BROKEN, image ? url : '', image);
    }

    function schedule(raw) {
        window.clearTimeout(timer);
        generation += 1;
        timer = window.setTimeout(() => check(raw), delay);
    }

    return {STATES, check, schedule};
};
