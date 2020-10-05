<template>
  <div class="has-margin-top-10">
    <b-field label="Show analysis after:">
      <b-timepicker
        v-model="timePicked"
        rounded
        placeholder="Click to select..."
        :time-formatter="dateFormater"
        icon="clock"
        :enable-seconds="enableSeconds"
        hour-format="24"
      ></b-timepicker>
    </b-field>
  </div>
</template>

<script>
import { convertUTCToTimeCode } from '../utils'
export default {
  data() {
    return {
      timePicked: this.$store.state.showSegmentAfter,
      enableSeconds: true
    }
  },
  methods: {
    dateFormater(date) {
      return convertUTCToTimeCode(date)
    }
  },
  watch: {
    timePicked: function() {
      this.$store.commit('setShowSegmentAfter', this.timePicked)
    }
  }
}
</script>

<style scoped></style>
