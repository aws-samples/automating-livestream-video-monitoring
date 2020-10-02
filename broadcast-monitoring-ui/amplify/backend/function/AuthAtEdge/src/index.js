/* Amplify Params - DO NOT EDIT
You can access the following resource attributes as environment variables from your Lambda function
var environment = process.env.ENV
var region = process.env.REGION
var authEncompassuidcbe520fUserPoolId = process.env.AUTH_ENCOMPASSUIDCBE520F_USERPOOLID

Amplify Params - DO NOT EDIT */

/* eslint-disable */

'use strict'
const jwt = require('jsonwebtoken')
const jwkToPem = require('jwk-to-pem')

const USERPOOLID = 'us-east-1_tK1PT2XHw' // process.env.AUTH_ENCOMPASSUIDCBE520F_USERPOOLID
// viewer request type of lambda@edge must have a package size < 1MB. this means we can't use the request package to
// download JWKS at run time.
const JWKS =
  '{"keys":[{"alg":"RS256","e":"AQAB","kid":"xkdwewjwW4xjcJRAzHswJd/VyINXdtiRHI7oUvTbSVU=","kty":"RSA","n":"iZ5rc2s00Fyz-h2VNDHeRkOzNIC__G-P-KzOTo6QykcfFjHD7BW1PVrkBrROArqjwx-ab4mvGZmma_-3Kiowe5mu-9B1m1VrxT1y5sYVWPgVcnLWXhqWiUrIq8XUGd1pGAYcp3Y08lD1ZlHwmoqqozfmHHM-yge7PH0j8MB0C1G8W0OPU7e7wm_KCUJQBzFSphh_6WbyEx8p5ukTH1GF3mjTHqHT9pDMMsLISaYiygm5FCJ7DpPq5XBp7r_dtvHCN0IB6jOEDJtPXPNXIdS7kCZUtMoNuROyjykNbR7Ob0aScodi3vWTj_-5wVCAJip0Hv_HRKQayLc8OnX_wVC7pQ","use":"sig"},{"alg":"RS256","e":"AQAB","kid":"3xLi/hXtmyz6FybUEQU1fjOAG9ZAUqxCg4eu23UgjW4=","kty":"RSA","n":"kQ8QB8VSRk1YuKJrpTydsEFJR8ObB8QuWcKSf1GYP8X8g3MAOTIaGXbFPxQS2GNgUUWENKue71Cqtqtk2D8uRCxnnELw6ZwwDJXG1GXk-VCjsHYls4fQWNcMRpuDF6RPbfG5sPnxCNpynI9SzkI4a4NUELDL-M0QaP8T5uw2dwE2ekGxHqgDYCCPeFXdnXoKLkzBQqQpFnQK_dQXd4j4yh-M18C1KCvWcdkV3Pj5ilKzjo7CBDP6sG3Z5v6zQyqel4Qw652uevjDW62PScFVFntq9hY14-Q1K9C9PfvUhoKasv2xWS-qa9Cp0XzxrxBwK-YWbo0POIywARCnRAzBFQ","use":"sig"}]}'
const region = 'us-east-1' // process.env.AWS_REGION //e.g. us-east-1
const iss = 'https://cognito-idp.' + region + '.amazonaws.com/' + USERPOOLID
let pems = {}

let keys = JSON.parse(JWKS).keys

for (var i = 0; i < keys.length; i++) {
  //Convert each key to PEM
  var key_id = keys[i].kid
  var modulus = keys[i].n
  var exponent = keys[i].e
  var key_type = keys[i].kty
  var jwk = { kty: key_type, n: modulus, e: exponent }
  var pem = jwkToPem(jwk)
  pems[key_id] = pem
}

const response401 = {
  status: '401',
  statusDescription: 'Unauthorized'
}

function validateToken(cfRequest, context, callback) {
  const headers = cfRequest.headers

  //Fail if no authorization header found
  if (!headers.authorization) {
    console.log('no auth header')
    callback(null, response401)
    return false
  }

  //strip out "Bearer " to extract JWT token only
  var jwtToken = headers.authorization[0].value.slice(7)
  console.log('jwtToken=' + jwtToken)

  //Fail if the token is not jwt
  var decodedJwt = jwt.decode(jwtToken, { complete: true })
  if (!decodedJwt) {
    console.log('Not a valid JWT token')
    callback(null, response401)
    return false
  }

  //Fail if token is not from your UserPool
  if (decodedJwt.payload.iss !== iss) {
    console.log('invalid issuer')
    callback(null, response401)
    return false
  }

  //Reject the jwt if it's not an 'Access Token'
  if (decodedJwt.payload.token_use !== 'access') {
    console.log('Not an access token')
    callback(null, response401)
    return false
  }

  //Get the kid from the token and retrieve corresponding PEM
  var kid = decodedJwt.header.kid
  var pem = pems[kid]
  if (!pem) {
    console.log('Invalid access token')
    callback(null, response401)
    return false
  }

  //Verify the signature of the JWT token to ensure it's really coming from your User Pool
  jwt.verify(jwtToken, pem, { issuer: iss }, function(err, payload) {
    if (err) {
      console.log('Token failed verification')
      console.log(err)
      callback(null, response401)
      return false
    } else {
      //Valid token.
      console.log('Successful verification')
      //remove authorization header
      delete cfRequest.headers.authorization
      //CloudFront can proceed to fetch the content from origin
      callback(null, cfRequest)
      return true
    }
  })
}

exports.handler = (event, context, callback) => {
  console.log('received event:\n' + JSON.stringify(event, null, 2))

  if (event.Records[0].cf.response) {
    /*
        This is a viewer response invocation.
        When using media package with cloudfront, the CORS response does not include "access-control-allow-headers"
        which will block the authorization header we use to authorize
         */
    console.log('viewer response. adding CORS headers')
    const response = event.Records[0].cf.response
    const headers = event.Records[0].cf.response.headers
    if ('origin' in event.Records[0].cf.request.headers) {
      console.log('viewer response. ')
      //The Request contains the Origin Header - Set CORS headers
      headers['access-control-allow-headers'] = [
        { key: 'Access-Control-Allow-Headers', value: '*' }
      ]
      headers['access-control-allow-origin'] = [{ key: 'Access-Control-Allow-Origin', value: '*' }]
      headers['access-control-allow-credentials'] = [
        { key: 'Access-Control-Allow-Credentials', value: 'true' }
      ]
    }
    //Return modified response
    callback(null, response)
    return
  }

  // otherwise, this is a viewer request invocation.
  const cfrequest = event.Records[0].cf.request
  console.log('USERPOOLID=' + USERPOOLID)
  console.log('region=' + region)

  // if the request is a CORS preflight, pass through
  if (cfrequest.method === 'OPTIONS') {
    callback(null, cfrequest)
    return
  }

  return validateToken(cfrequest, context, callback)
}
