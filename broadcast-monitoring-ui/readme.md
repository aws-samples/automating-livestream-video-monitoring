# Sample web app for Automating broadcast video monitoring

The web application is built using [AWS Amplify](https://docs.amplify.aws/), VueJS and uses AWS AppSync to communicate with backend databases.

## Project setup

1. If you haven't installed amplify CLI, do so:
   ```shell script
   sudo npm install -g @aws-amplify/cli
   ```
1. In the project root, install node dependencies:

   ```shell script
   npm install
   ```

1. Use pipenv to run a python script to replace template values with output from the backend cloudformation stack:

   ```
   # make setup_config.py executable
   chmod +x setup_config.py

   pipenv install
   pipenv run ./setup_config.py <replace with desired name of stack>
   ```

1. To use the existing amplify backend, set up amplify configuration

   ```
   $ amplify pull

   For more information on AWS Profiles, see:
   https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html

   ? Do you want to use an AWS profile? Yes
   ? Please choose the profile you want to use [default] <-- pick your own
   ? Which app are you working on? d2uuxfjdxgg2k4 <-- use the value presented by the CLI
   Backend environment 'dev' found. Initializing...
   ? Choose your default editor: Sublime Text    <-- pick your own
   ? Choose the type of app that you're building javascript
   Please tell us about your project
   ? What javascript framework are you using vue
   ? Source Directory Path:  src
   ? Distribution Directory Path: dist
   ? Build Command:  npm run build
   ? Start Command: npm run serve
   ```

1. pull backend environment setup from the cloud:

   ```shell script
   amplify pull
   ```

1. Verify that in `src/` folder, you should see a file `aws-exports.js` generated from previous step

### Compiles and hot-reloads for local development

```
npm run serve
```

### Compiles and minifies for production

```
npm run build
```

### Lints and fixes files

```
npm run lint
```

### Customize configuration

See [Configuration Reference](https://cli.vuejs.org/config/).
