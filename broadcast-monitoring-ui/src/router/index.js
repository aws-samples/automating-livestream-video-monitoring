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
 *
 * Note: this file was adapted from the sample at https://github.com/aws-samples/aws-amplify-vue/blob/master/src/router/index.js
 */

import Vue from 'vue';
import Router from 'vue-router';
import BroadcastMonitor from '@/components/BroadcastMonitor';
import Signin from '@/components/Signin';
import {AmplifyEventBus} from 'aws-amplify-vue';
import Amplify, * as AmplifyModules from 'aws-amplify';  // eslint-disable-line
import {AmplifyPlugin} from 'aws-amplify-vue';
import AmplifyStore from '../store/store';


Vue.use(Router);
Vue.use(AmplifyPlugin, AmplifyModules);

let user;

getUser().then((user) => {
  if (user) {
    router.push({path: '/'})
  }
})


AmplifyEventBus.$on('authState', async (state) => {
  console.log(state)  // eslint-disable-line
  if (state === 'signedOut') {
    user = null;
    AmplifyStore.commit('setUser', null);
    router.push({path: '/auth'})
  } else if (state === 'signedIn') {
    user = await getUser();
    router.push({path: '/'})
  }
});

function getUser() {
  return Vue.prototype.$Amplify.Auth.currentAuthenticatedUser().then((data) => {
    if (data && data.signInUserSession) {
      AmplifyStore.commit('setUser', data);
      return data;
    }
  }).catch((e) => {  // eslint-disable-line
    AmplifyStore.commit('setUser', null);
    return null
  });
}

const router = new Router({
  routes: [
    {
      path: '/',
      name: 'Home',
      component: BroadcastMonitor,
      meta: {requiresAuth: true}
    },
    {
      path: '/auth',
      name: 'Authenticator',
      component: Signin
    }
  ]
});

router.beforeResolve(async (to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    user = await getUser();
    if (!user) {
      return next({
        path: '/auth',
        query: {
          redirect: to.fullPath,
        }
      });
    }
    return next()
  }
  return next()
})

export default router
