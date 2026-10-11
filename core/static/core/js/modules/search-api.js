window.Songstery = window.Songstery || {};

/**
 * Клієнт підказок пошуку: скасування застарілих запитів, коротке кешування
 * та типізовані помилки, щоб UI міг показати зрозуміле повідомлення.
 */
window.Songstery.searchApi = (() => {
    const CACHE_LIMIT = 30;

    class SearchError extends Error {
        constructor(kind, message) {
            super(message);
            this.kind = kind;
        }
    }

    const ERROR_KINDS = Object.freeze({RATE_LIMITED: 'rate_limited', SERVER: 'server', NETWORK: 'network'});

    function createClient(url) {
        const cache = new Map();
        let controller = null;

        function remember(query, payload) {
            if (cache.size >= CACHE_LIMIT) cache.delete(cache.keys().next().value);
            cache.set(query, payload);
        }

        function abort() {
            controller?.abort();
            controller = null;
        }

        async function suggest(query) {
            const key = query.toLowerCase();
            if (cache.has(key)) return cache.get(key);

            abort();
            controller = new AbortController();
            let response;
            try {
                response = await fetch(`${url}?q=${encodeURIComponent(query)}`, {
                    signal: controller.signal,
                    headers: {Accept: 'application/json'},
                });
            } catch (error) {
                if (error.name === 'AbortError') throw error;
                throw new SearchError(ERROR_KINDS.NETWORK, error.message);
            }

            if (response.status === 429) throw new SearchError(ERROR_KINDS.RATE_LIMITED, 'Too many requests');
            if (!response.ok) throw new SearchError(ERROR_KINDS.SERVER, String(response.status));

            const payload = await response.json();
            remember(key, payload);
            return payload;
        }

        return {suggest, abort};
    }

    return {createClient, ERROR_KINDS};
})();
