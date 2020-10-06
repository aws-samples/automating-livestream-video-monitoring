<template>
  <div class="main">
    <div class="has-padding-15">
      <div class="columns">
        <div class="column is-one-third">
          <h2 class="is-size-3"><span class="has-text-weight-bold">Live</span>Stream</h2>
          <div class="has-text-left">
            <p class="is-size-6 is-uppercase">
              Current time
              <span
                class="has-padding-left-20 is-family-monospace has-text-weight-bold is-size-6"
                >{{ currentTime }}</span
              >
            </p>
          </div>

          <SidebarTimepicker />
        </div>
        <div class="column is-two-thirds">
          <div class="is-pulled-right">
            <video-player v-if="isLive" :options="videoOptions" />
            <div
              v-if="!isLive"
              id="video-loading"
              class="has-text-centered level rounder has-background-black has-text-white"
            >
              <div class="level-item">
                <div>
                  <progress class="progress is-small is-primary" max="100">15%</progress>
                  <p>Waiting for Live Stream to start...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import VideoPlayer from './VideoPlayer'
import SidebarTimepicker from './SidebarTimepicker'
import { convertUTCToTimeCode, parseMasterAndChildPlayList, isPlayListLive } from '../utils'
import { Auth } from 'aws-amplify'

export default {
  components: {
    VideoPlayer,
    SidebarTimepicker
  },
  data: function() {
    return {
      currentTime: convertUTCToTimeCode(new Date()),
      isLive: false,
      checkVideoInterval: null,
      videoOptions: {
        autoplay: true,
        controls: true,
        sources: [
          {
            src: this.$store.state.streamMasterUrl,
            type: 'application/x-mpegURL'
          }
        ]
      }
    }
  },
  mounted: async function() {
    setInterval(this.getNow, 100) // update the current time every 0.1 milliseconds.
    // ensure the credentials are available before making requests to cloudfront
    await Auth.currentCredentials()
    await this.checkVideoLiveliness()
    if (!this.isLive) {
      this.checkVideoInterval = setInterval(this.checkVideoLiveliness, 5000) // check if the stream is live every 5 seconds.
    }
  },
  methods: {
    checkVideoLiveliness: async function() {
      /**
       * Check whether the video feed is live or whether it's serving stale cached data.
       * This function reads the HLS master playlist, find the child playlist, and then read the program time stamp
       * from the child playlist. It compares current time against the time in the playlist to determin liveliness.
       */
      let parsedPlaylist = await parseMasterAndChildPlayList(this.$store.state.streamMasterUrl)
      // // download the master playlist
      if (isPlayListLive(parsedPlaylist)) {
        if (!this.isLive) {
          console.log('Video turned live! stop polling.') //eslint-disable-line
        }
        this.isLive = true
        if (this.checkVideoInterval) {
          clearInterval(this.checkVideoInterval)
        }
      } else {
        if (this.isLive) {
          console.log('Live video stopped!') //eslint-disable-line
        }
        this.isLive = false
      }
    },
    getNow: function() {
      this.currentTime = convertUTCToTimeCode(new Date())
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

.main {
  z-index: 0;
  position: relative;
}

.rounder {
  border-radius: 6px;
}
.video-js {
  max-width: 400px;
  max-height: 225px;
}

#video-loading {
  width: 400px;
  height: 225px;
}
</style>
