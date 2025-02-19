# CR8TOR Publish Service

The FastAPI based microservice supporting the [CR8TOR solution](https://github.com/lsc-sde-crates/cr8tor).

More description and Configuration details at [Service guide](./docs/service.md).

## Developer Guide

Please take the time to familiarize with the required [Configuration](./docs/service.md).

For Setting up local environment, working with Docker or Troubleshooting, see details at [Approval Service documentation](../approval-service/README.md#developer-guide).

### Troubleshooting

When running the Publish Service app in Windows, without the devcontainer and Docker, we need to set the `ARROW_TZDATA` environment variable. That way the dltHub can write out csv files with proper timezone configuration. Add the following code to your script:
   `os.environ['ARROW_TZDATA'] = r'C:\Users\{YOUR_USER_NAME}\Downloads\tzdata'`
See more details at:

- <https://stackoverflow.com/questions/76629191/arrowinvalid-cannot-locate-timezone-utc-timezone-database-not-found>
- <https://stackoverflow.com/questions/74267313/how-to-use-tzdata-file-with-pyarrow-compute-assume-timezone>
  