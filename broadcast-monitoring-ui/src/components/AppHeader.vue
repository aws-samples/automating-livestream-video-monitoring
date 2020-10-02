<template>
  <header class="is-full-width app-header has-background-white is-marginless">
    <div class="has-padding-10 has-padding-left-20 level">
      <div class="level-left">
        <h1 class="level-item is-size-5">
          <span class="has-text-weight-bold has-margin-right-5">AWS</span>
          Broadcast Monitoring
        </h1>
      </div>
      <div class="level-right level-item" id="user">
        <p class="has-text-right is-size-7">
          <span class="has-text-weight-bold">{{ userEmail }}</span>
          <br />
          <a class="is-size-7" href @click="signOut">Sign Out</a>
        </p>

        <div class="is-pulled-right has-padding-5">
          <span class="icon is-large has-text-grey-light">
            <i class="mdi mdi-48px mdi-account-circle"></i>
          </span>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import { Auth } from 'aws-amplify'

export default {
  data: function() {
    return {}
  },
  methods: {
    signOut() {
      Auth.signOut()
    }
  },
  computed: {
    user() {
      return this.$store.state.user
    },
    userEmail() {
      return this.$store.state.user.attributes.email
    }
  }
}
</script>

<style scoped>
.app-header {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  z-index: 90 !important;
  position: relative;
}

#sign-out {
  max-height: 65px;
}
</style>
