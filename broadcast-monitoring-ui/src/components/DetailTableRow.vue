<template>
  <tr class="has-text-grey">
    <td class="has-text-weight-bold">{{ checkName }}</td>
    <td>
      <span v-if="checkStatus !== null" class="icon is-small">
        <i class="mdi mdi-24px" :class="statusIconClass"></i>
      </span>
    </td>
    <td>
      <slot name="expected"></slot>
    </td>
    <td>
      <slot name="received"></slot>
    </td>
    <td v-if="confidence != null">
      <progress
        :class="'progress ' + confidenceColor(confidence)"
        :value="confidence"
        max="100"
      ></progress>
    </td>
    <td v-else>N/A</td>
    <td>
      <p v-if="confidence" class="is-pulled-right">{{ confidence.toFixed(2) }}%</p>
    </td>
  </tr>
</template>

<script>
export default {
  name: 'DetailTableRow',
  props: ['checkName', 'checkStatus', 'confidence'],
  methods: {
    confidenceColor: function(color) {
      if (color < 55) {
        return 'is-danger'
      } else if (color < 75) {
        return 'is-warning'
      } else {
        return 'is-success'
      }
    }
  },
  computed: {
    statusIconClass() {
      if (this.checkStatus) {
        return 'mdi-checkbox-marked-circle has-text-success'
      } else {
        return 'mdi-alert has-text-danger'
      }
    }
  }
}
</script>

<style scoped>
tr img {
  max-width: 160px;
}

table tr td {
  padding-top: 12px !important;
  padding-bottom: 8px !important;
}

progress {
  margin-bottom: 12px;
}
</style>
