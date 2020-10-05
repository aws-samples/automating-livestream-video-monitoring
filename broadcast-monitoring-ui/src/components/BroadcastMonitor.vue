<template>
  <div id="broadcast-monitor">
    <div id="app-header">
      <AppHeader />
    </div>
    <!--    <template v-if="$store.state.segmentListEmpty">-->
    <!--      <div id="app-empty-state" class="level">-->
    <!--        <EmptyState />-->
    <!--      </div>-->
    <!--    </template>-->
    <!--    <template v-else>-->
    <template>
      <div id="app-sidebar" class="has-background-white-ter">
        <Sidebar />
      </div>
      <div id="app-detail">
        <Detail />
      </div>
    </template>
  </div>
</template>

<script>
import AppHeader from './AppHeader'
import Sidebar from './Sidebar'
import Detail from './Detail'
// import EmptyState from './EmptyState'

export default {
  name: 'BroadcastMonitor',
  components: {
    AppHeader,
    Sidebar,
    Detail
    // EmptyState
  }
}
</script>

<style scoped>
#app-header {
  grid-column: 1 / 3;
}

#app-sidebar {
  grid-column: 1/2;
}

#app-empty-state {
  grid-column: 1/3;
  grid-row: 2/3;
  height: calc(100vh - 78px);
}
#broadcast-monitor {
  display: grid;
  grid-template-rows: 78px 1fr;
  grid-template-columns: 1fr 1fr;
  height: 100%;
}
</style>
