<template>
  <div id="app" v-if="hydrated">
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'app',
  data: () => ({ hydrated: false }),
  async mounted() {
    await this.$apollo.provider.defaultClient.hydrated()
    this.hydrated = true
  }
}
</script>

<style>
@import 'assets/styles/bulma-helpers.min.css';
@import 'assets/styles/custom.css';
@import url('https://fonts.googleapis.com/css?family=Roboto+Mono:400,700&display=swap');

html,
body {
  height: 100% !important;
}

.is-family-monospace {
  font-family: 'Roboto Mono', monospace !important;
}
</style>
