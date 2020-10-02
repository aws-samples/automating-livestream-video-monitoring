<template>
  <div class="has-margin-top-40">
    <ul>
      <li
        v-for="(frame, index) in frameDetails"
        :key="index"
        :class="{ active: index === activeFrame }"
        @click="selectFrame(index)"
      >
        <div>
          <detail-frame-thumbnail
            v-bind:issue-detected="frame.issueDetected"
            v-bind:thumbnail-s3-key="frame.Resized_S3_Key"
            v-bind:time-code="convertTimeCode(frame.DateTime)"
          ></detail-frame-thumbnail>
        </div>
      </li>
    </ul>
  </div>
</template>

<script>
import { convertUTCToTimeCode } from '../utils'
import DetailFrameThumbnail from './DetailFrameThumbnail'

export default {
  props: ['frameDetails'],
  components: { DetailFrameThumbnail },
  data: function() {
    return {
      activeFrame: 0
    }
  },
  methods: {
    selectFrame(selectedIndex) {
      this.activeFrame = selectedIndex
      this.$store.commit('setSelectedFrame', this.frameDetails[this.activeFrame])
    },
    convertTimeCode: convertUTCToTimeCode
  },
  watch: {
    frameDetails: function() {
      this.selectFrame(0)
    }
  },
  mounted() {
    this.selectFrame(0)
  }
}
</script>

<style scoped>
ul {
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
}

ul li {
  position: relative;
  padding-left: 10px;
  height: 120px;
}

ul li:hover {
  cursor: pointer;
}

ul li div {
  width: 90%;
  position: relative;
  margin: 0 auto;
  transition: width 0.2s ease-in-out;
}

ul li.active div {
  width: 100%;
}
</style>
