<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number
  }>(),
  {
    size: 24,
  },
)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M10 5H28L36 13V37C36 40.314 33.314 43 30 43H10C6.686 43 4 40.314 4 37V11C4 7.686 6.686 5 10 5Z"
      fill="white"
    />
    <path d="M28 5V12C28 12.552 28.448 13 29 13H36" fill="white" opacity="0.58" />
    <path d="M11 20H29M11 27H29M11 34H22" stroke="#6676DE" stroke-width="2.4" stroke-linecap="round" />
    <circle cx="36" cy="36" r="10" fill="#6676DE" stroke="white" stroke-width="2.4" />
    <path d="M31 36L34.3 39.3L41 32.6" stroke="white" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
