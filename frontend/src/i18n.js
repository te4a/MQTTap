import { writable, get } from 'svelte/store'

const STORAGE_KEY = 'mqttap.lang'
const modules = import.meta.glob('./i18n/*.json', { eager: true })
const translations = Object.fromEntries(
  Object.entries(modules).map(([path, mod]) => {
    const name = path.split('/').pop().replace('.json', '')
    return [name, mod.default || {}]
  })
)

const defaultLang = translations.ru ? 'ru' : Object.keys(translations)[0]
const initial = localStorage.getItem(STORAGE_KEY) || defaultLang
export const lang = writable(translations[initial] ? initial : defaultLang)

export function setLang(value) {
  if (!translations[value]) return
  localStorage.setItem(STORAGE_KEY, value)
  lang.set(value)
}

export function t(key, langCode = get(lang)) {
  return translations[langCode]?.[key] ?? translations.en[key] ?? key
}

export const availableLangs = Object.keys(translations).map((code) => ({
  value: code,
  label: translations[code]?.['lang.label'] || code.toUpperCase()
}))
