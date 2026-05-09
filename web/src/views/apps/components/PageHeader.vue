<template>
  <div class="page-header">
    <h1 class="page-title">{{ title }}</h1>
    <div class="page-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title: string
}>(), {})
</script>

<style scoped lang="scss">
.page-header {
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  margin: -24px;
  margin-bottom: 16px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;

  .page-title {
    color: #fff;
    font-size: 20px;
    font-weight: 600;
    margin: 0;
  }

  .page-actions {
    display: flex;
    gap: 8px;
  }
}
</style>
