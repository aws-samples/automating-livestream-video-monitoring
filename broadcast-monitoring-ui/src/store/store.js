/*
 * Copyright 2017-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with
 * the License. A copy of the License is located at
 *
 *     http://aws.amazon.com/apache2.0/
 *
 * or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
 * CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

const store = new Vuex.Store({
  state: {
    stream_id: 'demo_1280_720', // set the stream ID here vs. config file to allow selecting different streams in the future.
    streamUrlPrefix: process.env.VUE_APP_VIDEO_MASTER_MANIFEST.substring(0, process.env.VUE_APP_VIDEO_MASTER_MANIFEST.indexOf('index')),
    streamMasterManifest: process.env.VUE_APP_VIDEO_MASTER_MANIFEST.substring(process.env.VUE_APP_VIDEO_MASTER_MANIFEST.indexOf('index')),
    streamMasterUrl: process.env.VUE_APP_VIDEO_MASTER_MANIFEST,
    useCNDAuth: false, // whether the video stream is configured for auth (lambda@edge)
    user: null,
    showSegmentAfter: new Date(),
    latestSegment: null,
    manualSegmentSelect: false,
    selectedSegmentStartTime: null,
    segmentListLoading: true,
    segmentListEmpty: true,
    selectedFrame: null
  },
  mutations: {
    setUser(state, user) {
      state.user = user
    },
    manualSelectSegment(state, selectedSegmentStartTime) {
      state.manualSegmentSelect = true
      state.selectedSegmentStartTime = selectedSegmentStartTime
    },
    autoSelectSegment(state) {
      state.manualSegmentSelect = false
      state.selectedSegmentStartTime = state.latestSegment
    },
    setLatestSegment(state, latestSegment) {
      state.latestSegment = latestSegment
      if (!state.manualSegmentSelect) {
        state.selectedSegmentStartTime = state.latestSegment
      }
    },
    setSegmenListStatus(state, listStatus) {
      state.segmentListLoading = listStatus.loading
      state.segmentListEmpty = listStatus.isEmpty
    },
    setSelectedFrame(state, selectedFrame) {
      state.selectedFrame = selectedFrame
    },
    setShowSegmentAfter(state, showSegmentAfter) {
      state.showSegmentAfter = showSegmentAfter
    }
  },
  getters: {
    authToken: state => {
      if (state.user) {
        return state.user.signInUserSession.accessToken.jwtToken
      } else {
        return null
      }
    }
  }
})

export default store
