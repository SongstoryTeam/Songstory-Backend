window.Songstery = window.Songstery || {};

window.Songstery.dom = (() => {
    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function readJson(root, selector) {
        const node = root.querySelector(selector);
        return node ? JSON.parse(node.textContent) : {};
    }

    function format(template, values) {
        return template.replace(/\{(\w+)\}/g, (match, key) => (key in values ? values[key] : match));
    }

    return {element, readJson, format};
})();
