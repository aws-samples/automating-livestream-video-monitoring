import moment from 'moment'
import { Parser as M3u8Parser } from 'm3u8-parser'
import store from './store/store'
import Axios from 'axios'

function convertUTCToTimeCode(dateTimeUTCStr) {
  return moment(dateTimeUTCStr).format('HH:mm:ss:SS')
}

function timeDiffMillis(dateTimeA, dateTimeB) {
  return moment(dateTimeA) - moment(dateTimeB)
}

async function downloadPlaylist(playlistUrl) {
  let headers = {}
  if (store.state.useCNDAuth) {
    let authToken = `Bearer ${store.getters.authToken}`
    headers = { authorization: authToken }
  }

  let masterManifestRes = await Axios.get(playlistUrl, { headers })
  return masterManifestRes.data
}

async function parseMasterAndChildPlayList(masterUrl) {
  let masterPlayList = await downloadPlaylist(masterUrl)
  let parsedMasterPlaylist = parsePlaylist(masterPlayList)
  if (!parsedMasterPlaylist.playlists) {
    console.log('Did not find playlist from stream') //eslint-disable-line
    return null
  }

  // download the child playlist
  let childPlaylistUrl = store.state.streamUrlPrefix + parsedMasterPlaylist.playlists[0].uri
  let childPlaylist = await downloadPlaylist(childPlaylistUrl)
  let parsedChildPlaylist = parsePlaylist(childPlaylist)
  return parsedChildPlaylist
}

function parsePlaylist(m3u8Manifest) {
  let parser = new M3u8Parser()
  parser.push(m3u8Manifest)
  parser.end()
  return parser.manifest
}

function isPlayListLive(playlistManifest) {
  if (playlistManifest.dateTimeObject === undefined) {
    console.log('Did not find video program time.') //eslint-disable-line
    return
  }
  let programDateTime = playlistManifest.dateTimeObject
  if (playlistManifest.discontinuityStarts.length > 0) {
    console.log(`Found discontinuity: ${playlistManifest.discontinuityStarts}`) //eslint-disable-line
    let discontinuityIndex = playlistManifest.discontinuityStarts[0]
    let discontinuitySegment = playlistManifest.segments[discontinuityIndex]
    programDateTime = discontinuitySegment.dateTimeObject
  }

  let playlistTimeDiffMillis = new Date() - programDateTime

  console.log(`Video program time behind now: ${playlistTimeDiffMillis / 1000} seconds.`) //eslint-disable-line
  return playlistTimeDiffMillis < 100000
}

export { timeDiffMillis, convertUTCToTimeCode, isPlayListLive, parseMasterAndChildPlayList }
