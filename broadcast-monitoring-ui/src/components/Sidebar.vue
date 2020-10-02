<template>
  <div class="container has-padding-10 is-pulled-right" id="app-sidebar-content">
    <div>
      <SidebarVideoStream />
    </div>
    <div>
      <SidebarTable />
    </div>
  </div>
</template>

<script>
import SidebarVideoStream from './SidebarVideoStream'
import SidebarTable from './SidebarTable'

export default {
  components: {
    SidebarVideoStream,
    SidebarTable
  }
}
</script>

<style scoped>
.container {
  display: grid;
  grid-template-rows: 1fr 3fr;
  max-height: calc(100vh - 78px);
  width: 100%;
}

.container div:nth-of-type(2) {
  overflow-y: scroll;
}
</style>
