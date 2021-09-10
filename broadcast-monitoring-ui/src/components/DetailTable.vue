<template>
  <div>
    <table class="table is-fullwidth is-narrow is-size-7">
      <thead>
        <tr>
          <th>Check</th>
          <th>Status</th>
          <th>Expected</th>
          <th>Received</th>
          <th>Confidence</th>
          <th></th>
        </tr>
      </thead>
      <detail-table-row
        check-name="Audio"
        v-if="audioCheck && audioCheck.Audio_Status !== null"
        v-bind:check-status="audioCheck.Audio_Status"
        v-bind:confidence="audioCheck.Confidence"
      >
        <template v-slot:received>
          <p>
            Silence: {{ audioCheck.Silence_Duration.toFixed(1) }}/{{ segmentDuration.toFixed(1) }}
            sec
          </p>
          <p>Avg. Volume: {{ audioCheck.Mean_DB }} dB</p>
        </template>
        <template v-slot:expected>
          <p>No Silence</p>
        </template>
      </detail-table-row>
      <detail-table-row
        check-name="Sports"
        v-if="frameDetail && frameDetail.Sports_Check && frameDetail.Sports_Check.Expected_Sports"
        v-bind:check-status="frameDetail.Sports_Check.Status"
        v-bind:confidence="frameDetail.Sports_Check.Confidence"
      >
        <template v-slot:expected>
          <p>{{ frameDetail.Sports_Check.Expected_Sports }}</p>
        </template>
        <template v-slot:received>
          <p>{{ frameDetail.Sports_Check.Detected_Sports }}</p>
        </template>
      </detail-table-row>
      <detail-table-row
        check-name="Team 1"
        v-if="frameDetail && frameDetail.Team_Check && frameDetail.Team_Check.Team1_Expected"
        v-bind:check-status="frameDetail.Team_Check.Team1_Status"
        v-bind:confidence="frameDetail.Team_Check.Team1_Confidence"
      >
        <template v-slot:expected>
          <DetailTableTeams :team-details="team1ExpectDetails" />
        </template>
        <template v-slot:received>
          <DetailTableTeams :team-details="team1DetectDetails" />
        </template>
      </detail-table-row>
      <detail-table-row
        check-name="Team 2"
        v-if="frameDetail && frameDetail.Team_Check && frameDetail.Team_Check.Team2_Expected"
        v-bind:check-status="frameDetail.Team_Check.Team2_Status"
        v-bind:confidence="frameDetail.Team_Check.Team2_Confidence"
      >
        <template v-slot:expected>
          <DetailTableTeams :team-details="team2ExpectDetails" />
        </template>
        <template v-slot:received>
          <DetailTableTeams :team-details="team2DetectDetails" />
        </template>
      </detail-table-row>
      <detail-table-row
        check-name="Station Logo"
        v-if="frameDetail && frameDetail.Logo_Check && frameDetail.Logo_Check.Expected_Logo"
        v-bind:check-status="frameDetail.Logo_Check.Status"
        v-bind:confidence="frameDetail.Logo_Check.Confidence"
      >
        <template v-slot:received>
          <div v-if="frameDetail.Logo_Check.Detected_Logo">
            <p>
              {{ frameDetail.Logo_Check.Detected_Logo }}
              <br />
              <img v-if="cropLogoSrc" :src="cropLogoSrc" />
            </p>
          </div>
          <div v-else-if="frameDetail.Logo_Check.Error">
            <p>{{ frameDetail.Logo_Check.Error }}</p>
          </div>
        </template>
        <template v-slot:expected>
          <p>{{ frameDetail.Logo_Check.Expected_Logo }}</p>
        </template>
      </detail-table-row>
    </table>
  </div>
</template>

<script>
import { Storage } from 'aws-amplify'
import DetailTableRow from './DetailTableRow'
import DetailTableTeams from './DetailTableTeams'

export default {
  props: ['frameDetail', 'audioCheck', 'segmentDuration'],
  components: { DetailTableRow, DetailTableTeams },
  data: function() {
    return {
      frameData: '',
      cropLogoSrc: null
    }
  },
  methods: {
    alertStatus: function(status) {
      if (status === true) {
        return 'mdi-alert has-text-alert'
      } else {
        return 'mdi-home'
      }
    },
    confidenceColor: function(color) {
      if (color < 75) {
        return 'is-danger'
      } else if (color < 90) {
        return 'is-warning'
      } else {
        return 'is-success'
      }
    }
  },
  watch: {
    /* eslint-disable no-unused-vars */
    frameDetail: async function(newFrameDetail, oldFrameDetail) {
      if (
        newFrameDetail &&
        newFrameDetail.Logo_Check &&
        newFrameDetail.Logo_Check.Detected_Logo_Crop_S3_Key
      ) {
        this.cropLogoSrc = await Storage.get(newFrameDetail.Logo_Check.Detected_Logo_Crop_S3_Key)
        return
      }
      this.cropLogoSrc = null
    }
  },
  computed: {
    team1ExpectDetails() {
      if (
        this.frameDetail &&
        this.frameDetail.Team_Check &&
        this.frameDetail.Team_Check.Team1_Expected
      ) {
        return [{ name: this.frameDetail.Team_Check.Team1_Expected }]
      } else {
        return null
      }
    },
    team2ExpectDetails() {
      if (
        this.frameDetail &&
        this.frameDetail.Team_Check &&
        this.frameDetail.Team_Check.Team2_Expected
      ) {
        return [{ name: this.frameDetail.Team_Check.Team2_Expected }]
      } else {
        return null
      }
    },
    team1DetectDetails() {
      if (
        this.frameDetail &&
        this.frameDetail.Team_Check &&
        this.frameDetail.Team_Check.Team1_Expected
      ) {
        let teamDetails = []
        if (this.frameDetail.Team_Check.Team1_Detected_Text) {
          teamDetails.push({
            name: this.frameDetail.Team_Check.Team1_Detected_Text,
            source: 'text'
          })
        }
        if (this.frameDetail.Team_Check.Team1_Detected_Logo) {
          teamDetails.push({
            name: this.frameDetail.Team_Check.Team1_Detected_Logo,
            source: 'logo'
          })
        }
        return teamDetails
      } else {
        return null
      }
    },
    team2DetectDetails() {
      if (
        this.frameDetail &&
        this.frameDetail.Team_Check &&
        this.frameDetail.Team_Check.Team2_Expected
      ) {
        let teamDetails = []
        if (this.frameDetail.Team_Check.Team2_Detected_Text) {
          teamDetails.push({
            name: this.frameDetail.Team_Check.Team2_Detected_Text,
            source: 'text'
          })
        }
        if (this.frameDetail.Team_Check.Team2_Detected_Logo) {
          teamDetails.push({
            name: this.frameDetail.Team_Check.Team2_Detected_Logo,
            source: 'logo'
          })
        }
        return teamDetails
      } else {
        return null
      }
    }
  }
}
</script>

<style scoped>
>>> table tr:last-of-type td {
  border-bottom: 0px;
}

.active {
  opacity: 1;
  animation-name: flashon;
  animation-duration: 1.2s;
}

@keyframes flashon {
  from {
    opacity: 0;
    border-width: 2px;
  }
  to {
    opacity: 1;
    border-width: 10px;
  }
}
</style>
