from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeOption:
    value: str
    label: str
    hint: str
    icon: str


THEME_OPTIONS: tuple[ThemeOption, ...] = (
    ThemeOption("light", "Світла", "Теплі світлі тони для денного читання", "sun"),
    ThemeOption("dark", "Темна", "Спокійний контраст для вечора та ночі", "moon"),
    ThemeOption("system", "Як в системі", "Автоматично, за налаштуванням пристрою", "monitor"),
)
