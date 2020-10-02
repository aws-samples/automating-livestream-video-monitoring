<template>
  <video ref="videoPlayer" class="video-js rounder"></video>
</template>

<script>
import videojs from 'video.js'
import store from '../store/store'
export default {
  name: 'VideoPlayer',
  props: {
    seekEnabled: {
      type: Boolean,
      default() {
        return false
      }
    },
    seekPosition: {
      type: Number,
      default() {
        return 0
      }
    },
    options: {
      type: Object,
      default() {
        return {}
      }
    }
  },
  data() {
    return {
      player: null
    }
  },
  created() {
    let self = this
    if (store.state.useCNDAuth) {
      videojs.Hls.xhr.beforeRequest = function(options) {
        // console.log(options) //eslint-disable-line
        options.headers = {}
        if (self.$store.getters.authToken) {
          options.headers.authorization = `Bearer ${self.$store.getters.authToken}`
        }
      }
    }
  },
  mounted() {
    this.player = videojs(this.$refs.videoPlayer, this.options, function onPlayerReady() {
      console.log('onPlayerReady', this) //eslint-disable-line
    })
  },
  watch: {
    options: function(newOptions, oldOptions) {
      console.log('video option changed. new options:') //eslint-disable-line
      console.log(newOptions) //eslint-disable-line
      console.log(oldOptions) //eslint-disable-line
      this.player.src(newOptions.sources[0])
    },
    seekPosition: function(newOffset) {
      if (this.seekEnabled && newOffset >= 0) {
        this.player.currentTime(newOffset)
      }
    }
  },
  beforeDestroy() {
    if (this.player) {
      this.player.dispose()
    }
  }
}
</script>

<style scoped>
@import '~video.js/dist/video-js.css';

>>> .vjs-big-play-button {
  left: 40%;
  top: 40%;
  width: 20%;
  height: 20%;
}
</style>
