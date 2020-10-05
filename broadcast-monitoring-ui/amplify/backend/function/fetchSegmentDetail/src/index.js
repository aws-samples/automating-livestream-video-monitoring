/* Amplify Params - DO NOT EDIT
You can access the following resource attributes as environment variables from your Lambda function
var environment = process.env.ENV
var region = process.env.REGION

Amplify Params - DO NOT EDIT */

/* eslint-disable */

const AWS = require('aws-sdk')
const util = require('util')
const moment = require('moment')

const segments_table = process.env.SEGMENT_TABLE
const frame_table = process.env.FRAME_TABLE
const documentClient = new AWS.DynamoDB.DocumentClient({ region: process.env.AWS_REGION })

function parseAudioCheckResult(segmentItem) {
  let audioResult = {}
  if (segmentItem.Audio_Status !== undefined) {
    audioResult = {
      Audio_Status: segmentItem.Audio_Status,
      Silence_Duration: segmentItem.Silence_Duration,
      Confidence: segmentItem.Silence_Confidence,
      Mean_DB: segmentItem.Volume.mean
    }
  }
  return audioResult
}

function getMaxConfidenceDetection(detections) {
  if (detections === undefined || detections.length == 0) {
    return { Name: null }
  }
  return detections.reduce((max, el) => (max.Confidence > el.Confidence ? max : el))
}

function parseFrameTeamCheckResult(frameResults) {
  if (!frameResults.Team1_Text_Expected) {
    return {}
  }

  const {
    Team1_Text_Expected = { name: undefined },
    Team1_Logo_Expected = { name: undefined },
    Team1_Detection_Confidence: Team1_Confidence = 0.0,
    Team1_Text_Detected = [],
    Team1_Logo_Detected = [],
    Team1_Status = null,
    Team2_Text_Expected = { name: undefined },
    Team2_Logo_Expected = { name: undefined },
    Team2_Text_Detected = [],
    Team2_Logo_Detected = [],
    Team2_Detection_Confidence: Team2_Confidence = 0.0,
    Team2_Status = null,
    Expected_Teams = []
  } = frameResults

  const { name: Team1_Detected_Logo } = getMaxConfidenceDetection(Team1_Logo_Detected)
  const { name: Team2_Detected_Logo } = getMaxConfidenceDetection(Team2_Logo_Detected)

  const team1TextDetected = Team1_Text_Detected.length > 0 ? Team1_Text_Detected[0].name : null
  const team2TextDetected = Team2_Text_Detected.length > 0 ? Team2_Text_Detected[0].name : null
  console.log(`team 1 detected: ${team1TextDetected}; team 2 detected: ${team2TextDetected}`)
  return {
    Team1_Expected: Team1_Text_Expected.name || Team1_Logo_Expected.name,
    Team1_Detected_Text: team1TextDetected,
    Team1_Detected_Logo,
    Team1_Status,
    Team1_Confidence,
    Team2_Expected: Team2_Text_Expected.name || Team2_Logo_Expected.name,
    Team2_Detected_Text: team2TextDetected,
    Team2_Detected_Logo,
    Team2_Status,
    Team2_Confidence,
    Status: Team1_Status && Team2_Status,
    Expected_Teams,
    Detected_Teams: []
  }
}

function parseLogoCheckResult(frameResults) {
  let logoResult = {}
  if (frameResults.Expected_Logo !== undefined) {
    logoResult = {
      Status: frameResults.Is_Expected_Logo,
      Expected_Logo: frameResults.Expected_Logo,
      Detected_Logo: frameResults.Detected_Logo || 'MISSING',
      Detected_Logo_Crop_S3_Key: frameResults.Detected_Station_Logo_Crop_S3_KEY,
      Confidence: frameResults.Detected_Logo_Confidence || null,
      Error: frameResults.Logo_Detect_Error || null
    }
  }
  return logoResult
}

function parseSportsCheckResult(frameResults) {
  let sportsResult = {}
  if (frameResults.Sports_Expected !== undefined) {
    sportsResult = {
      Status: frameResults.Sports_Status,
      Expected_Sports: frameResults.Sports_Expected,
      Detected_Sports: frameResults.Sports_Detected || 'MISSING',
      Confidence: frameResults.Sports_Detected_Confidence || null
    }
  }
  return sportsResult
}

/**
 * Using this as the entry point, you can use a single function to handle many resolvers.
 */
const resolvers = {
  Query: {
    /**
     * Fetches details about a particular video segments and its analysis results,
     *  including analysis on extracted frames
     * @param ctx
     * @returns {Promise<{Frames: [],   (list of details about individual frames)
     *            Duration_Sec: float,  (duration of the segment)
     *            Silence_Duration: float,  (duration of the silence)
     *            Stream_ID: string, (video stream identifer)
     *            Start_DateTime: string,  (YYYY-MM-DDTHH:mm:ss.SSSSSSZ UTC format)
     *            End_DateTime: string,    (YYYY-MM-DDTHH:mm:ss.SSSSSSZ UTC format)
     *            S3_Key: string}>}
     */
    getSegmentDetails: async ctx => {
      let segmentTableParams = {
        TableName: segments_table,
        KeyConditionExpression: 'Stream_ID = :streamid and Start_DateTime = :startdt',
        ExpressionAttributeValues: {
          ':streamid': ctx.arguments.Stream_ID,
          ':startdt': ctx.arguments.Start_DateTime
        }
      }

      try {
        let segmentsTableEntry = await documentClient.query(segmentTableParams).promise()
        console.log(`query segment table got ${segmentsTableEntry.Count} results.`)
        let segmentItem = segmentsTableEntry.Items[0]
        let startDateTimeStr = segmentItem.Start_DateTime
        let durationSec = segmentItem.Duration_Sec
        let endDateTime = moment.utc(startDateTimeStr).add(durationSec, 'seconds')
        let endDateTimeStr = endDateTime.format('YYYY-MM-DDTHH:mm:ss.SSSSSS') + 'Z'
        console.log(`segment: ${startDateTimeStr} - ${endDateTimeStr}. duration: ${durationSec}`)
        let segmentId = `${ctx.arguments.Stream_ID}:${segmentItem.Start_DateTime}`

        let frameTableParams = {
          TableName: frame_table,
          IndexName: 'Segment_Millis',
          KeyConditionExpression: '#segment = :segment',
          ExpressionAttributeNames: {
            '#segment': 'Segment'
          },
          ExpressionAttributeValues: {
            ':segment': segmentId
          }
        }

        let frameTableResults = await documentClient.query(frameTableParams).promise()
        console.log(`query segment table got ${frameTableResults.Count} results.`)
        let frames = []
        frameTableResults.Items.forEach(frameResults => {
          const { S3_Key, Resized_S3_Key, DateTime } = frameResults
          let parsedFrameResults = { S3_Key, Resized_S3_Key, DateTime }

          parsedFrameResults.Team_Check = parseFrameTeamCheckResult(frameResults) || {}
          const {
            Team1_Status: team1Status = null,
            Team2_Status: team2Status = null
          } = parsedFrameResults.Team_Check
          const teamIssueDetected =
            (team1Status != null && team1Status === false) ||
            (team2Status != null && team2Status === false)

          parsedFrameResults.Logo_Check = parseLogoCheckResult(frameResults) || {}
          const { Status: logoStatus = true } = parsedFrameResults.Logo_Check

          parsedFrameResults.Sports_Check = parseSportsCheckResult(frameResults) || {}
          const { Status: sportsStatus = true } = parsedFrameResults.Sports_Check

          parsedFrameResults.issueDetected = teamIssueDetected || !logoStatus || !sportsStatus
          frames.push(parsedFrameResults)
        })
        return {
          Stream_ID: ctx.arguments.Stream_ID,
          Start_DateTime: startDateTimeStr,
          End_DateTime: endDateTimeStr,
          Duration_Sec: durationSec,
          Audio_Check: parseAudioCheckResult(segmentItem),
          S3_Key: segmentItem.S3_Key,
          Frames: frames
        }
      } catch (e) {
        console.log(e)
        throw new Error(`NOT FOUND`)
      }
    }
  }
}

// event
// {
//   "typeName": "Query", /* Filled dynamically based on @function usage location */
//   "fieldName": "me", /* Filled dynamically based on @function usage location */
//   "arguments": { /* GraphQL field arguments via $ctx.arguments */ },
//   "identity": { /* AppSync identity object via $ctx.identity */ },
//   "source": { /* The object returned by the parent resolver. E.G. if resolving field 'Post.comments', the source is the Post object. */ },
//   "request": { /* AppSync request object. Contains things like headers. */ },
//   "prev": { /* If using the built-in pipeline resolver support, this contains the object returned by the previous function. */ },
// }
exports.handler = async event => {
  console.log('Reading input from event:\n', util.inspect(event, { depth: 5 }))
  const typeHandler = resolvers[event.typeName]
  if (typeHandler) {
    const resolver = typeHandler[event.fieldName]
    if (resolver) {
      return await resolver(event)
    }
  }
  throw new Error('Resolver not found.')
}
