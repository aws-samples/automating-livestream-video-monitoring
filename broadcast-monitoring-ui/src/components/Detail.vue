<template>
  <div class="container" v-if="getSegmentDetails">
    <section class="section">
      <div class="columns">
        <div class="column is-one-third">
          <h2 class="is-size-4 has-text-link">
            Sample
            <span class="has-text-weight-bold">Inspector</span>
          </h2>
          <div>
            <span class="is-size-7">
              Start
              <br />
            </span>

            <span class="is-size-5 has-text-weight-bold is-family-monospace">
              {{ convertTimeCode(getSegmentDetails.Start_DateTime) }}
            </span>
          </div>
          <div>
            <span class="is-size-7">
              End
              <br />
            </span>
            <span class="is-size-5 has-text-weight-bold is-family-monospace">
              {{ convertTimeCode(getSegmentDetails.End_DateTime) }}
            </span>
          </div>
        </div>
        <div class="column is-two-thirds">
          <video-player
            :options="videoOptions"
            :seek-enabled="true"
            :seek-position="playbackSeekPosition"
          />
        </div>
      </div>
      <DetailFrames v-bind:frame-details="getSegmentDetails.Frames" />
      <DetailTable
        v-bind:frame-detail="this.$store.state.selectedFrame"
        v-bind:audio-check="getSegmentDetails.Audio_Check"
        v-bind:segment-duration="getSegmentDetails.Duration_Sec"
      />
    </section>
  </div>
</template>

<script>
import DetailFrames from './DetailFrames'
import DetailTable from './DetailTable'
import VideoPlayer from './VideoPlayer'
import { GET_SEGMENT_DETAILS } from '../graphql/queries'
import { convertUTCToTimeCode, timeDiffMillis, parseMasterAndChildPlayList } from '../utils' // eslint-disable-line

export default {
  components: {
    DetailFrames,
    DetailTable,
    VideoPlayer
  },
  data: function() {
    return {
      getSegmentDetails: null,
      playbackSeekPosition: 0,
      playlistStartTime: null
    }
  },
  computed: {
    srcUrl: function() {
      if (this.getSegmentDetails) {
        const { Start_DateTime: start, End_DateTime: end } = this.getSegmentDetails
        const rawUrl = this.$store.state.streamMasterUrl
        return start && end ? `${rawUrl}?start=${start}&end=${end}` : rawUrl
      } else {
        return null
      }
    },
    videoOptions: function() {
      return {
        aspectRatio: '16:9',
        autoplay: false,
        controls: true,
        sources: [
          {
            src: this.srcUrl,
            type: 'application/x-mpegURL'
          }
        ]
      }
    },
    selectedFrameStartTime: function() {
      if (this.$store.state.selectedFrame) {
        return this.$store.state.selectedFrame.DateTime
      }
      return null
    }
  },
  methods: {
    convertTimeCode: convertUTCToTimeCode,
    backToLatest: function() {
      this.$store.commit('autoSelectSegment')
    }
  },
  watch: {
    srcUrl: async function(newSrcUrl) {
      this.playbackSeekPosition = 0
      let parsedPlaylist = await parseMasterAndChildPlayList(newSrcUrl)
      // console.log(parsedPlaylist) //eslint-disable-line
      this.playlistStartTime = parsedPlaylist.dateTimeObject
      let offset = timeDiffMillis(this.getSegmentDetails.Start_DateTime, this.playlistStartTime)
      this.playbackSeekPosition = offset / 1000
    },
    selectedFrameStartTime: function(newStartTime, oldStartTime) {
      if (newStartTime) {
        /* eslint no-console: ["error", { allow: ["log", "error"] }] */
        console.log(
          `Selective playback old start: ${oldStartTime}; old seek position: ${this.playbackSeekPosition}`
        )
        let offset = timeDiffMillis(newStartTime, this.playlistStartTime) / 1000
        if (offset >= 0) {
          this.playbackSeekPosition = offset
          console.log(
            `Selective playback new start: ${newStartTime} new seek position: ${this.playbackSeekPosition}`
          )
        }
      }
    }
  },
  apollo: {
    getSegmentDetails: {
      query: GET_SEGMENT_DETAILS,
      variables() {
        return {
          Stream_ID: this.$store.state.stream_id,
          Start_DateTime: this.$store.state.selectedSegmentStartTime
        }
      },
      error(error) {
        console.log(error) // eslint-disable-line no-console
      },
      skip() {
        let shouldSkip = this.$store.state.segmentListLoading || this.$store.state.segmentListEmpty
        // do not attempt to load the segment detail until the segment list has finished loading
        return shouldSkip
      }
    }
  }
}
</script>

<style scoped>
>>> .video-js {
  width: 100%;
}
</style>
