const MenuControl = (() => {
    const ROOT_SELECTOR = '[data-menu]';
    const TOGGLE_SELECTOR = '[data-menu-toggle]';
    const PANEL_SELECTOR = '[data-menu-panel]';
    const ITEM_SELECTOR = '[role="menuitem"]:not([aria-disabled="true"])';
    const ALIGN_END = 'end';

    function parts(menu) {
        return {toggle: menu.querySelector(TOGGLE_SELECTOR), panel: menu.querySelector(PANEL_SELECTOR)};
    }

    function items(menu) {
        return [...parts(menu).panel.querySelectorAll(ITEM_SELECTOR)];
    }

    function isOpen(menu) {
        return !parts(menu).panel.hidden;
    }

    function openMenus() {
        return [...document.querySelectorAll(ROOT_SELECTOR)].filter(isOpen);
    }

    function alignWithinViewport(panel) {
        delete panel.dataset.align;
        if (panel.getBoundingClientRect().right > document.documentElement.clientWidth) {
            panel.dataset.align = ALIGN_END;
        }
    }

    function open(menu) {
        const {toggle, panel} = parts(menu);
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        alignWithinViewport(panel);
        items(menu)[0]?.focus();
    }

    function close(menu, {restoreFocus = true} = {}) {
        if (!isOpen(menu)) return;
        const {toggle, panel} = parts(menu);
        panel.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        if (restoreFocus) toggle.focus();
    }

    function closeOthers(current) {
        openMenus().filter((menu) => menu !== current).forEach((menu) => close(menu, {restoreFocus: false}));
    }

    function moveFocus(menu, step) {
        const list = items(menu);
        if (!list.length) return;
        const index = list.indexOf(document.activeElement);
        const next = index === -1 ? (step > 0 ? 0 : list.length - 1) : (index + step + list.length) % list.length;
        list[next].focus();
    }

    function focusEdge(menu, last) {
        const list = items(menu);
        list.at(last ? -1 : 0)?.focus();
    }

    const KEY_HANDLERS = {
        ArrowDown: (menu) => (isOpen(menu) ? moveFocus(menu, 1) : open(menu)),
        ArrowUp: (menu) => (isOpen(menu) ? moveFocus(menu, -1) : open(menu)),
        Home: (menu) => isOpen(menu) && focusEdge(menu, false),
        End: (menu) => isOpen(menu) && focusEdge(menu, true),
    };

    function onClick(event) {
        const toggle = event.target.closest(TOGGLE_SELECTOR);
        const menu = toggle?.closest(ROOT_SELECTOR) ?? null;
        closeOthers(menu);
        if (!menu) return;
        if (isOpen(menu)) {
            close(menu);
        } else {
            open(menu);
        }
    }

    function onKeydown(event) {
        const menu = event.target.closest(ROOT_SELECTOR);

        if (event.key === 'Escape') {
            openMenus().forEach((current) => close(current, {restoreFocus: current === menu}));
            return;
        }
        if (event.key === 'Tab' && menu) {
            close(menu, {restoreFocus: false});
            return;
        }
        const handler = menu && KEY_HANDLERS[event.key];
        if (!handler) return;
        event.preventDefault();
        handler(menu);
    }

    function init() {
        if (!document.querySelector(ROOT_SELECTOR)) return;
        document.addEventListener('click', onClick);
        document.addEventListener('keydown', onKeydown);
    }

    return {init, open, close};
})();

document.addEventListener('DOMContentLoaded', MenuControl.init);
