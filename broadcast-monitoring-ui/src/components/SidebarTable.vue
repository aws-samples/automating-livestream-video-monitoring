<template>
  <div id="app-sidebar-table">
    <div v-if="$apollo.queries.listSegmentSummary.loading">Loading...</div>
    <div v-if="listSegmentSummary">
      <table class="table is-fullwidth">
        <!-- TABLE HEADER  -->
        <thead class="has-background-grey-dark">
          <tr>
            <th
              class="is-size-7 has-padding-top-10 is-narrow has-text-white-ter"
              v-for="(check, ch) in checks"
              :key="ch"
            >
              <span class="icon is-small">
                <i :class="'mdi mdi-18px mdi-' + check.icon"></i>
              </span>
              <br />
              {{ check.name }}
            </th>
          </tr>
        </thead>
        <!-- SAMPLES -->
        <tr
          v-for="segment in listSegmentSummary.items"
          class="is-size-7 check-row"
          :key="segment.Start_DateTime"
          :class="{ active: segment.Start_DateTime === $store.state.selectedSegmentStartTime }"
          @click="selectSegment(segment.Start_DateTime)"
        >
          <td class="has-text-weight-bold">{{ getTimeCode(segment.Start_DateTime) }}</td>
          <td class="thumbnail">
            <amplify-s3-image v-bind:img-key="segment.Thumbnail_Key"></amplify-s3-image>
          </td>
          <td>
            <span class="icon is-small">
              <i :class="'mdi mdi-24px mdi-' + alertCheck(segment.Audio_Status)"></i>
            </span>
          </td>
          <td>
            <span class="icon is-small">
              <i :class="'mdi mdi-24px mdi-' + alertCheck(segment.Station_Status)"></i>
            </span>
          </td>
          <td>
            <span class="icon is-small">
              <i :class="'mdi mdi-24px mdi-' + alertCheck(segment.Sports_Status)"></i>
            </span>
          </td>
          <td>
            <span class="icon is-small">
              <i :class="'mdi mdi-24px mdi-' + alertCheck(segment.Team_Status)"></i>
            </span>
          </td>
        </tr>
      </table>
    </div>
  </div>
</template>

<script>
import { convertUTCToTimeCode } from '../utils'
import { LIST_SEGMENTS } from '../graphql/queries'
import { SEGMENT_SUBSCRIPTION } from '../graphql/subscriptions'
import moment from 'moment'

export default {
  data: function() {
    return {
      checks: [
        { name: 'Time', icon: 'filmstrip' },
        { name: 'Thumbnail', icon: 'image-area' },
        { name: 'Audio', icon: 'volume-high' },
        { name: 'Logo', icon: 'television' },
        { name: 'Sports', icon: 'soccer' },
        { name: 'Teams', icon: 'account-group' }
      ]
    }
  },
  methods: {
    getTimeCode(dateTimeStr) {
      return convertUTCToTimeCode(dateTimeStr)
    },

    alertCheck(status) {
      if (status === undefined || status === null) {
        // if we don't get a particular status, we treat that check as being disabled.
        return 'alarm-off'
      } else if (status === true) {
        return 'checkbox-marked-circle has-text-success'
      } else {
        return 'alert has-text-danger'
      }
    },
    selectSegment(selectedSegmentStartTime) {
      this.$store.commit('manualSelectSegment', selectedSegmentStartTime)
    }
  },
  apollo: {
    listSegmentSummary: {
      // graphql query
      query: LIST_SEGMENTS,
      variables() {
        return {
          Stream_ID: this.$store.state.stream_id,
          After: this.$store.state.showSegmentAfter,
          limit: 100 // set to 0 to simulate no data
        }
      },
      error(error) {
        console.log(error) // eslint-disable-line no-console
      },
      result({ data, loading }) {
        let isResultEmpty =
          data == null ||
          data.listSegmentSummary == null ||
          data.listSegmentSummary.items == null ||
          data.listSegmentSummary.items.length === 0
        this.$store.commit('setSegmenListStatus', { loading: loading, isEmpty: isResultEmpty })
        if (!loading && data && data.listSegmentSummary.items[0]) {
          this.$store.commit('setLatestSegment', data.listSegmentSummary.items[0].Start_DateTime)
        }
      }
    },
    $subscribe: {
      /* eslint-disable no-console */
      newSegmentSummaryAdded: {
        query: SEGMENT_SUBSCRIPTION,
        variables() {
          return {
            Stream_ID: this.$store.state.stream_id
          }
        },
        error(error) {
          console.log('error with newSegmentSummaryAdded subscription') // eslint-disable-line no-console
          console.log(error) // eslint-disable-line no-console
        },
        result(data) {
          if (data.data.newSegmentSummaryAdded) {
            this.$store.commit('setSegmenListStatus', { loading: false, isEmpty: false })
          }
          if (
            !this.listSegmentSummary ||
            !this.listSegmentSummary.items ||
            this.listSegmentSummary.items.length === 0
          ) {
            let items = [data.data.newSegmentSummaryAdded] || []
            this.listSegmentSummary = { items: items }
            this.$store.commit('setLatestSegment', data.data.newSegmentSummaryAdded.Start_DateTime)
            return
          }
          let newSegmentStartTime = data.data.newSegmentSummaryAdded.Start_DateTime
          for (let i = 0; i < this.listSegmentSummary.items.length; i++) {
            let currentSegmentStartTime = this.listSegmentSummary.items[i].Start_DateTime
            if (moment(newSegmentStartTime).isAfter(currentSegmentStartTime)) {
              console.log(
                `Inserting new record ${currentSegmentStartTime} before ${currentSegmentStartTime}`
              )
              this.listSegmentSummary.items.splice(i, 0, data.data.newSegmentSummaryAdded)
              break
            } else if (moment(newSegmentStartTime).isSame(currentSegmentStartTime)) {
              console.log(`new record ${currentSegmentStartTime} already exists`)
              break
            }
          }
          this.$store.commit('setLatestSegment', this.listSegmentSummary.items[0].Start_DateTime)
        }
      }
    }
  }
}
</script>

<style scoped>
th {
  position: sticky;
  top: 0px;
  background-color: #43415c !important;
}

.table td {
  vertical-align: middle !important;
}

.table tr {
  height: 59px;
}

.table td img {
  height: 50px;
}

.active,
.table tr:nth-of-type(1).active {
  color: #fff;
  box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.2);
}

.table tr:nth-of-type(1).active td {
  background-color: #3b85fe !important;
}

tr.check-row {
  cursor: pointer;
}

.active td {
  position: sticky !important;
  top: 110px;
  background-color: #3b85fe !important;
}

.table tr:nth-of-type(1) td {
  position: sticky;
  background-color: #fff;
  top: 52px;
}

table tr:first-of-type td:first-of-type::before {
  content: 'Latest';
  text-transform: uppercase;
  font-weight: 200;
  letter-spacing: 0.1em;
  display: block;
}

/*https://docs.amplify.aws/ui/storage/s3-image/q/framework/react/#props-css-amplify-s3-image*/
amplify-s3-image {
  --width: 50% !important;
  margin: 0 !important;
}
</style>
