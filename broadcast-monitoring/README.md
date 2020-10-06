Broadcast monitoring
===================


### Development 
Before committing your code and submitting a PR, please run the test suite (including flake8 linter) and make sure all tests passes. 
```shell script
./run_tests.sh
```

### Deployment 

The repo for backend processing is set up to be auto deployed by CodeBuild when the master branch has new commits (configured through `buildspec.yml` in the project root. )

To deploy a separate stack for development purposes, run the deploy script from the project root.

```
sh deploy.sh <name-of-env>
```
