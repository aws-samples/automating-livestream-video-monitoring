<template>
  <div>
    <div class="is-block">
      <span v-for="(detail, i) in teamDetails" :key="i">
        <span class="has-text-weight-bold has-padding-left-5 has-padding-right-5">{{
          detail.name
        }}</span>
        <div v-if="detail.source" class="tag is-dark has-margin-bottom-5 ">
          {{ detail.source }}
        </div>
      </span>
    </div>
  </div>
</template>

<script>
export default {
  props: ['teamDetails']
}
</script>

<style scoped></style>
