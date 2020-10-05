import gql from 'graphql-tag'

export const LIST_SEGMENTS = gql`
  query listSegmentSummary(
    $Stream_ID: String!
    $After: AWSDateTime
    $nextToken: String
    $limit: Int
  ) {
    listSegmentSummary(
      Stream_ID: $Stream_ID
      After: $After
      nextToken: $nextToken
      limit: $limit
    ) {
      items {
        Start_DateTime
        Duration_Sec
        S3_Key
        Station_Status
        Audio_Status
        Team_Status
        Sports_Status
        Thumbnail_Key
      }
      nextToken
    }
  }
`

export const GET_SEGMENT_DETAILS = gql`
  query GetSegmentDetails($Stream_ID: String!, $Start_DateTime: AWSDateTime!) {
    getSegmentDetails(Stream_ID: $Stream_ID, Start_DateTime: $Start_DateTime) {
      Stream_ID
      Start_DateTime
      End_DateTime
      Duration_Sec
      Audio_Check {
        Audio_Status
        Silence_Duration
        Mean_DB
        Confidence
      }
      S3_Key
      Frames {
        S3_Key
        Resized_S3_Key
        DateTime
        Sports_Check {
          Status
          Expected_Sports
          Detected_Sports
          Confidence
        }
        Logo_Check {
          Status
          Expected_Logo
          Detected_Logo
          Detected_Logo_Crop_S3_Key
          Confidence
          Error
        }
        Team_Check {
          Status
          Team1_Expected
          Team1_Detected_Text
          Team1_Detected_Logo
          Team1_Confidence
          Team1_Status
          Team2_Status
          Team2_Expected
          Team2_Detected_Text
          Team2_Detected_Logo
          Team2_Confidence
          Expected_Teams
          Detected_Teams
        }
        issueDetected
      }
    }
  }
`
