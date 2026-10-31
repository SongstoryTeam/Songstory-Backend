window.Songstery = window.Songstery || {};

window.Songstery.createAvatarCrop = ({stage, fields, onChange}) => {
    const KEYBOARD_PAN_PX = 8;
    const AXES = Object.freeze(['x', 'y']);
    const ARROW_DIRECTIONS = Object.freeze({
        ArrowLeft: {x: -1, y: 0},
        ArrowRight: {x: 1, y: 0},
        ArrowUp: {x: 0, y: -1},
        ArrowDown: {x: 0, y: 1},
    });
    const ZOOM_DIRECTIONS = Object.freeze({'+': 1, '=': 1, '-': -1, _: -1});

    const boundsOf = (field) => ({
        min: Number(field.getAttribute('min')),
        max: Number(field.getAttribute('max')),
        step: Number(field.getAttribute('step')) || 1,
        initial: Number(field.value),
        fallback: Number(field.dataset.default),
    });

    const bounds = {x: boundsOf(fields.x), y: boundsOf(fields.y), zoom: boundsOf(fields.zoom)};
    const state = {x: bounds.x.initial, y: bounds.y.initial, zoom: bounds.zoom.initial};

    let natural = null;
    let drag = null;

    const clamp = (name, value) => Math.min(bounds[name].max, Math.max(bounds[name].min, value));
    const span = (name) => bounds[name].max - bounds[name].min;

    function overflow(axis) {
        if (!natural) return 0;
        const size = stage.clientWidth;
        const fit = Math.max(size / natural.width, size / natural.height);
        const length = axis === 'x' ? natural.width : natural.height;
        return Math.max(length * fit * (state.zoom / bounds.zoom.min) - size, 0);
    }

    function set(changes) {
        Object.entries(changes).forEach(([name, value]) => {
            state[name] = clamp(name, value);
        });
        onChange({...state});
    }

    function panBy(delta) {
        const changes = {};
        AXES.forEach((axis) => {
            const room = overflow(axis);
            if (room) changes[axis] = state[axis] - (delta[axis] / room) * span(axis);
        });
        set(changes);
    }

    function endDrag() {
        drag = null;
        stage.classList.remove('is-dragging');
    }

    stage.addEventListener('pointerdown', (event) => {
        if (!natural || event.button !== 0) return;
        drag = {x: event.clientX, y: event.clientY};
        stage.setPointerCapture(event.pointerId);
        stage.classList.add('is-dragging');
    });

    stage.addEventListener('pointermove', (event) => {
        if (!drag) return;
        panBy({x: event.clientX - drag.x, y: event.clientY - drag.y});
        drag = {x: event.clientX, y: event.clientY};
    });

    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach((type) => stage.addEventListener(type, endDrag));

    stage.addEventListener('keydown', (event) => {
        if (!natural) return;
        const direction = ARROW_DIRECTIONS[event.key];
        if (direction) {
            event.preventDefault();
            panBy({x: direction.x * KEYBOARD_PAN_PX, y: direction.y * KEYBOARD_PAN_PX});
            return;
        }
        const zoomDirection = ZOOM_DIRECTIONS[event.key];
        if (zoomDirection) {
            event.preventDefault();
            set({zoom: state.zoom + zoomDirection * bounds.zoom.step});
        }
    });

    return {
        get state() {
            return {...state};
        },
        setImage(image) {
            natural = image ? {width: image.naturalWidth, height: image.naturalHeight} : null;
            stage.toggleAttribute('data-ready', Boolean(natural));
        },
        setZoom(value) {
            set({zoom: value});
        },
        reset() {
            set({x: bounds.x.fallback, y: bounds.y.fallback, zoom: bounds.zoom.fallback});
        },
    };
};
