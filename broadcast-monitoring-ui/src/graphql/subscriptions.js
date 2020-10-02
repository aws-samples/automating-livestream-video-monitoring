import gql from 'graphql-tag'

export const SEGMENT_SUBSCRIPTION = gql`
  subscription NewSegmentSummaryAdded($Stream_ID: String!) {
    newSegmentSummaryAdded(Stream_ID: $Stream_ID) {
      Start_DateTime
      Duration_Sec
      S3_Key
      Language_Status
      Station_Status
      Audio_Status
      Team_Status
      Thumbnail_Key
    }
  }
`
