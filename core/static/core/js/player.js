const Player = (() => {
    const PLATFORM_COLORS = {
        youtube:    '#FF0000',
        spotify:    '#1DB954',
        soundcloud: '#FF5500',
        other:      'var(--clr-accent)',
    };

    const PLATFORM_LABELS = {
        youtube:    'YouTube',
        spotify:    'Spotify',
        soundcloud: 'SoundCloud',
        other:      'Link',
    };

    let currentTrackId = null;
    let currentLinkUrl = '#';

    const bar        = document.getElementById('sticky-player');
    const embedArea  = document.getElementById('player-embed-area');
    const titleEl    = document.getElementById('player-title');
    const artistEl   = document.getElementById('player-artist');
    const platformEl = document.getElementById('player-platform');
    const dotEl      = document.getElementById('player-dot');
    const openBtn    = document.getElementById('player-open');
    const closeBtn   = document.getElementById('player-close');

    function buildSpotifyEmbed(code) {
        return `https://open.spotify.com/embed/track/${code}?utm_source=generator&theme=0`;
    }

    function buildSoundCloudEmbed(url) {
        return `https://w.soundcloud.com/player/?url=${encodeURIComponent(url)}&color=%23c4622d&auto_play=false&hide_related=true&show_comments=false&show_user=false&show_reposts=false&show_teaser=false`;
    }

    function buildYouTubeThumbnail(code, title, artist, linkUrl) {
        const thumb = `https://img.youtube.com/vi/${code}/mqdefault.jpg`;
        return `
            <div class="yt-preview">
                <img src="${thumb}" alt="${title}" class="yt-preview__thumb"
                     onerror="this.style.display='none'">
                <div class="yt-preview__overlay">
                    <svg class="yt-preview__icon" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                </div>
                <a href="${linkUrl}" target="_blank" rel="noopener" class="yt-preview__link">
                    Відкрити на YouTube
                </a>
            </div>
        `;
    }

    function renderEmbed(linkType, embedCode, linkUrl) {
        embedArea.innerHTML = '';

        if (linkType === 'youtube') {
            embedArea.innerHTML = buildYouTubeThumbnail(embedCode, '', '', linkUrl);
            embedArea.className = 'player__embed player__embed--youtube';
            return;
        }

        const iframe = document.createElement('iframe');
        iframe.id = 'player-iframe';
        iframe.frameBorder = '0';
        iframe.allow = 'autoplay; encrypted-media; picture-in-picture';

        if (linkType === 'spotify' && embedCode) {
            iframe.src = buildSpotifyEmbed(embedCode);
            iframe.allow += '; clipboard-write';
            embedArea.className = 'player__embed player__embed--spotify';
        } else if (linkType === 'soundcloud') {
            iframe.src = buildSoundCloudEmbed(linkUrl);
            iframe.scrolling = 'no';
            embedArea.className = 'player__embed player__embed--soundcloud';
        } else {
            embedArea.className = 'player__embed';
        }

        embedArea.appendChild(iframe);
    }

    function load(trackId, title, artist, linkType, embedCode, linkUrl) {
        if (currentTrackId === trackId) {
            toggle();
            return;
        }

        if (!embedCode && linkType !== 'soundcloud' && linkType !== 'other') {
            window.open(linkUrl, '_blank', 'noopener,noreferrer');
            return;
        }

        if (linkType === 'other') {
            window.open(linkUrl, '_blank', 'noopener,noreferrer');
            return;
        }

        currentTrackId = trackId;
        currentLinkUrl = linkUrl;

        titleEl.textContent = title;
        artistEl.textContent = artist;
        platformEl.textContent = PLATFORM_LABELS[linkType] || linkType;
        dotEl.style.background = PLATFORM_COLORS[linkType] || 'var(--clr-accent)';
        openBtn.href = linkUrl;

        renderEmbed(linkType, embedCode, linkUrl);

        bar.classList.remove('player--hidden');
        bar.classList.add('player--visible');

        updateActiveButton(trackId);
    }

    function toggle() {
        const hidden = bar.classList.contains('player--hidden');
        bar.classList.toggle('player--hidden', !hidden);
        bar.classList.toggle('player--visible', hidden);
    }

    function close() {
        embedArea.innerHTML = '';
        currentTrackId = null;
        bar.classList.remove('player--visible');
        bar.classList.add('player--hidden');
        clearActiveButtons();
    }

    function updateActiveButton(trackId) {
        clearActiveButtons();
        const btn = document.querySelector(`.play-btn[data-track-id="${trackId}"]`);
        if (btn) btn.classList.add('play-btn--active');
    }

    function clearActiveButtons() {
        document.querySelectorAll('.play-btn--active').forEach(el => {
            el.classList.remove('play-btn--active');
        });
    }

    function init() {
        if (!bar) return;

        closeBtn?.addEventListener('click', close);

        document.querySelectorAll('.play-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                load(
                    btn.dataset.trackId,
                    btn.dataset.title,
                    btn.dataset.artist,
                    btn.dataset.linkType,
                    btn.dataset.embedCode,
                    btn.dataset.linkUrl,
                );
            });
        });
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', Player.init);