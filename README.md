<a name="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

## About The Project

### Overview

This package was created by factoring out many reusable code artifacts from my [various projects][tailucas-url] over a number of years. Since this work was not a part of a group effort, the test coverage is predictably abysmal :raised_eyebrow: and Python documentation notably absent :expressionless:. For each of my projects, which derive from a common Docker application [found here][baseapp-url], this package provides some specific and relatively powerful features to enable rapid offshoots for new ideas.

The package is organized under `src/tailucas_pylib/` with the following key modules:

* **Core Modules:**
  - `__init__.py`: Application bootstrap with logging, locale, configuration (via `app.conf`), and device name setup. Logs to syslog (UDP) or stdout/stderr. Optionally changes working directory to `WORK_DIR`.
  - `creds.py`: 1Password credential management supporting both [1Password Connect Server](https://github.com/1Password/connect-sdk-python) and [1Password Service Account](https://github.com/1Password/onepassword-sdk-python) modes. Fetches secrets from environment variables or container secrets (`/run/secrets`).
  - `flags.py`: Feature flag checking backed by a 1Password credential item.

* **Application Framework:**
  - `app.py`: Thread base class with ZMQ relay (`ZmqRelay`) and worker (`ZmqWorker`) patterns for inter-thread communication via [ZeroMQ][zmq-url].
  - `threads.py`: Thread nanny with shutdown tracking, graceful termination, Cronitor monitoring integration, and lingering socket cleanup.
  - `handler.py`: Context manager (`exception_handler`) that handles ZMQ connectivity, `ContextTerminated`, `ResourceWarning`, and general exceptions with optional Sentry reporting and graceful shutdown.
  - `process.py`: Signal handler (`SignalHandler`) with subprocess execution (`exec_cmd`) helpers.

* **Communication:**
  - `rabbit.py`: [RabbitMQ][rabbit-url] integration with `MQConnection`, `ZMQListener` (consumes RabbitMQ messages and forwards to ZMQ), and `RabbitMQRelay` (bridges ZMQ to RabbitMQ).
  - `zmq.py`: [ZeroMQ][zmq-url] socket creation, lifecycle management (`Closable`), and graceful context teardown.

* **Utilities:**
  - `data.py`: Builds MessagePack payloads with timestamp and optional data for IPC.
  - `datetime.py`: Timezone-aware timestamp creation, ISO formatting, and Unix timestamp conversion.
  - `device.py`: Pydantic data model (`Device`) for device state with optional fields.
  - `bluetooth.py`: Bluetooth adaptor detection and device ping via `hcitool` / `l2ping`.

* **AWS Integration (`aws/`):**
  - `__init__.py`: Manages cached Boto3 sessions with STS role assumption, credential retrieval from 1Password.
  - `metrics.py`: Posts CloudWatch count metrics with dimensions.

* **Command-line Tools (`tools/`):**
  - `config_interpol.py`: Interpolates a config file with environment variables or an overlay config, outputting the resolved values.
  - `cred_tool.py`: Fetches and displays a 1Password credential read from stdin.
  - `yaml_interpol.py`: Processes YAML templates, substituting values from configuration sections.
  - `aws_configure.py`: Generates AWS CLI configuration files from 1Password-stored credentials.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

Technologies that help make this package useful:

[![1Password][1p-shield]][1p-url]
[![Amazon AWS][aws-shield]][aws-url]
[![uv][uv-shield]][uv-url]
[![Python][python-shield]][python-url]
[![RabbitMQ][rabbit-shield]][rabbit-url]
[![Sentry][sentry-shield]][sentry-url]
[![ZeroMQ][zmq-shield]][zmq-url]

Also:

* [Cronitor][cronitor-url]
* [MessagePack][msgpack-url]

![GitHub](https://img.shields.io/static/v1?style=for-the-badge&message=GitHub&color=181717&logo=GitHub&logoColor=FFFFFF&label=)

* [Botoflow][botoflow-url]

Core Technologies:
- **Python 3.8+** - Primary runtime
- **1Password Connect/Service Account** - Credential management
- **ZeroMQ** - Inter-process communication
- **RabbitMQ** - Message queuing
- **MessagePack** - Binary serialization
- **Pydantic** - Data validation and modeling
- **Sentry** - Error tracking and monitoring

AWS Integration:
- **Boto3** - AWS SDK
- **CloudWatch** - Metrics and monitoring
- **Simple Workflow Service** - Workflow orchestration (deprecated)

Development Tools:
- **uv** - Dependency management
- **Cronitor** - Cron job monitoring

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

Here is some detail about the intended use of this package.

### Prerequisites

A [Python][python-url] project or runtime environment. Since this project is already initialized with [uv][vu-url] dependency management, I recommend that you continue to use it. Beyond the Python dependencies defined in the [configuration](pyproject.toml), the package init carries hardcoded dependencies on [Sentry][sentry-url] and [1Password][1p-url] in order to function. Unless you want these and are effectively extending my [base project][baseapp-url], you're likely better off forking this package and cutting out what you do not need.

### Installation

This package is published to the [Python Package index](https://pypi.org/project/tailucas-pylib/) from time to time.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

I have [various projects][tailucas-url] that use this tool chain. For example, my [Base Project](https://github.com/tailucas/base-app) which can be run stand-alone but also serves as my [Docker base image](https://hub.docker.com/repository/docker/tailucas/base-app/tags?page=1&ordering=last_updated) from which other projects are derived.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Template on which this README is based](https://github.com/othneildrew/Best-README-Template)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/tailucas/pylib.svg?style=for-the-badge
[contributors-url]: https://github.com/tailucas/pylib/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/tailucas/pylib.svg?style=for-the-badge
[forks-url]: https://github.com/tailucas/pylib/network/members
[stars-shield]: https://img.shields.io/github/stars/tailucas/pylib.svg?style=for-the-badge
[stars-url]: https://github.com/tailucas/pylib/stargazers
[issues-shield]: https://img.shields.io/github/issues/tailucas/pylib.svg?style=for-the-badge
[issues-url]: https://github.com/tailucas/pylib/issues
[license-shield]: https://img.shields.io/github/license/tailucas/pylib.svg?style=for-the-badge
[license-url]: https://github.com/tailucas/pylib/blob/master/LICENSE

[baseapp-url]: https://github.com/tailucas/base-app
[tailucas-url]: https://github.com/tailucas

[1p-url]: https://developer.1password.com/docs/connect/
[1p-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=1Password&color=0094F5&logo=1Password&logoColor=FFFFFF&label=
[aws-url]: https://aws.amazon.com/
[aws-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=Amazon+AWS&color=232F3E&logo=Amazon+AWS&logoColor=FFFFFF&label=
[botoflow-url]: https://github.com/boto/botoflow
[cronitor-url]: https://cronitor.io/
[msgpack-url]: https://msgpack.org/
[uv-url]: https://docs.astral.sh/uv/
[uv-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=uv&color=60A5FA&logo=uv&logoColor=FFFFFF&label=
[python-url]: https://www.python.org/
[python-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=Python&color=3776AB&logo=Python&logoColor=FFFFFF&label=
[rabbit-url]: https://www.rabbitmq.com/
[rabbit-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=RabbitMQ&color=FF6600&logo=RabbitMQ&logoColor=FFFFFF&label=
[sentry-url]: https://sentry.io/
[sentry-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=Sentry&color=362D59&logo=Sentry&logoColor=FFFFFF&label=
[zmq-url]: https://zeromq.org/
[zmq-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=ZeroMQ&color=DF0000&logo=ZeroMQ&logoColor=FFFFFF&label=
