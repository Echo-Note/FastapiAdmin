<script lang="ts" setup>
const {
  enabled: watermarkEnabled,
  content: watermarkContent,
  color: watermarkColor,
  width: watermarkWidth,
  height: watermarkHeight,
  opacity: watermarkOpacity,
} = useWatermark()
</script>

<script lang="ts">
export default {
  options: {
    addGlobalClass: true,
    virtualHost: true,
    styleIsolation: 'shared',
  },
}
</script>

<template>
  <slot />
  <wd-watermark
    v-if="watermarkEnabled"
    :content="watermarkContent"
    :color="watermarkColor"
    :width="watermarkWidth"
    :height="watermarkHeight"
    :opacity="watermarkOpacity"
    layout="grid"
  />
</template>
