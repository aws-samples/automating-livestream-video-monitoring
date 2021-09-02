<template>
  <div>
    <img :src="url" />
    <div class="timestamp is-size-7 has-text-weight-bold has-text-white is-family-monospace">
      {{ timeCode }}
    </div>
    <span class="icon is-small">
      <i
        :class="
          'mdi mdi-24px ' +
            [
              issueDetected
                ? 'mdi-alert has-text-danger'
                : 'mdi-checkbox-marked-circle has-text-success'
            ]
        "
      ></i>
    </span>
  </div>
</template>

<script>
import { Storage } from 'aws-amplify'
export default {
  name: 'DetailFrameThumbnail',
  props: {
    thumbnailS3Key: {
      type: String,
      default: ''
    },
    issueDetected: {
      type: Boolean,
      default: false
    },
    timeCode: {
      type: String,
      default: '00:00:00:00'
    }
  },
  data: function() {
    return {
      url: null
    }
  },
  mounted() {
    Storage.get(this.thumbnailS3Key)
      .then(url => {
        this.url = url
      })
      .catch(e => {
        console.log(e) //eslint-disable-line
      })
  },
  watch: {
    thumbnailS3Key: function(newS3Key) {
      Storage.get(newS3Key)
        .then(url => {
          this.url = url
        })
        .catch(e => {
          console.log(e) //eslint-disable-line
        })
    }
  }
}
</script>

<style scoped>
.timestamp {
  display: block;
  position: absolute;
  background-color: #000;
  border-radius: 2px;
  padding: 0.25rem 0.5rem 0.5rem;
  z-index: 1;
  top: -2rem;
  left: 0;
  height: 2rem;
  visibility: hidden;
  border: 1px solid black;
}

ul li.active .timestamp {
  visibility: visible;
  top: initial;
  bottom: -1.5rem;
}

ul li:hover .timestamp {
  visibility: visible;
  background-color: #fff;
  color: #000 !important;
}

.icon {
  position: absolute;
  width: 24px;
  height: 24px;
  bottom: 15%;
  left: 5%;
  text-shadow: 0 0 4px rgba(0, 0, 0, 0.8);
}

img {
  max-width: 100%;
  max-height: 80px;
  transition: margin-top 0.2s ease-in-out;
}

ul li.active div img {
  box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.3);
  margin-top: -5%;
}
</style>
