<a name="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

## About The Project

### Overview

This package was created by factoring out many reusable code artifacts from my [various projects][tailucas-url] over a number of years. Since this work was not a part of a group effort, the test coverage is predictably abysmal :raised_eyebrow: and Python documentation notably absent :expressionless:. For each of my projects, which derive from a common Docker application [found here][baseapp-url], this package provides some specific and relatively powerful features to enable rapid offshoots for new ideas. Here is what functionality this package provides:

* [aws.__init__.py](https://github.com/tailucas/pylib/blob/master/pylib/aws/__init__.py): If AWS environment variables are set, global boto and boto3 session objects are instantiated.
* [aws.metrics](https://github.com/tailucas/pylib/blob/master/pylib/aws/metrics.py): CloudWatch metric helper.
* [aws.swf](https://github.com/tailucas/pylib/blob/master/pylib/aws/swf.py): Client-side interface to [botoflow][botoflow-url] with interfaces specific to a number of prior projects. Examples of this use are in respective *swf* branches of some projects. This mechanism has been since replaced with message passing via [RabbitMQ][rabbit-url].
* [__init__.py](https://github.com/tailucas/pylib/blob/master/pylib/__init__.py): A lot of module bootstrap with a pitiful attempt to support unit testing. At application startup, a choice is made between logging to a configured logger or to the terminal if one exists, to support a scenario where the application is run interactively. A standard application configuration file is loaded with a Python ConfigParser and then a credentials client is loaded based on [1Password][1p-url]. The choice of 1Password is motivated by their secrets automation features and because I happened to use their service already. I have been tempted to try Bitwarden also but there has not been a need yet to create this abstraction. Next, the [Sentry][sentry-url] client is loaded with whatever extras the given application might specify. Then Python builtins are ~~ab~~used to store some globals for use throughout the package and application.
* [app](https://github.com/tailucas/pylib/blob/master/pylib/app.py): A few of my applications use [ZeroMQ][zmq-url] for "lockless" IPCs between Python threads and so it became apparent that some helpers were needed to support common patterns. [ZmqRelay](https://github.com/tailucas/pylib/blob/a950b0f5fd9e539899e046bbcf5dbad4a02a1347/pylib/app.py#LL26C7-L26C15) is one such example where an application thread can be used to receive some message on which processing is done, and then forward it to another ZeroMQ channel. The main thread logic is contained with a context manager which handles failures and shutdown gracefully.
* [app.bluetooth](https://github.com/tailucas/pylib/blob/master/pylib/bluetooth.py): Bluetooth helper functions that make use of [hcitool](https://linux.die.net/man/1/hcitool) *l2ping*.
* [app.data](https://github.com/tailucas/pylib/blob/master/pylib/data.py): Simple utility to make a common IPC or network payload using [MessagePack][msgpack-url].
* [app.datetime](https://github.com/tailucas/pylib/blob/master/pylib/datetime.py): Date and timestamp manipulation with time zone normalization.
* [app.handler](https://github.com/tailucas/pylib/blob/a950b0f5fd9e539899e046bbcf5dbad4a02a1347/pylib/handler.py#L16): A useful Python context manager to handle a variety of failure conditions.
* [app.process](https://github.com/tailucas/pylib/blob/master/pylib/process.py): Simple signal handler with interaction with application shutdown tracking.
* [app.rabbit](https://github.com/tailucas/pylib/blob/master/pylib/rabbit.py): A fairly good example of a [RabbitMQ][rabbit-url] application framework with internal IPC handoff to [ZeroMQ][zmq-url] channels for inter-thread communication.
* [app.threads](https://github.com/tailucas/pylib/blob/master/pylib/threads.py): A useful thread nanny with shutdown debugging and metric support.
* [app.zmq](https://github.com/tailucas/pylib/blob/master/pylib/zmq.py): Useful helper functions for a [ZeroMQ][zmq-url] enabled application.

Handy stand-alone tools:

* [config_interpol](https://github.com/tailucas/pylib/blob/master/config_interpol): By making creative ~~ab~~use of Python's ConfigParser, this tool designed for the command-line will take a configuration file with variables that are automatically substituted with with either an overlay configuration or environment variables by the same name and output the interpolated configuration. A good example of this tool being used is [here](https://github.com/tailucas/base-app/blob/723bbef3a4f5380d722dae52bcb52537b4e44bc1/base_entrypoint.sh#L5).
* [cred_tool](https://github.com/tailucas/pylib/blob/master/cred_tool): Useful to fetch an item from [1Password][1p-url].
* [yaml_interpol](https://github.com/tailucas/pylib/blob/master/yaml_interpol): A script useful to generate docker-compose YAML output from templates. A crude example is [here](https://github.com/tailucas/base-app/blob/723bbef3a4f5380d722dae52bcb52537b4e44bc1/Makefile#LL21C47-L21C47) which fetches application configuration from a 1Password vault. Note that application runtime secrets are only in memory and loaded in [__init__.py](https://github.com/tailucas/pylib/blob/master/pylib/__init__.py). I happen to use 1Password to also store application key-value pairs for use in docker-compose templates.

### Package Structure

A crude attempt to visualize the package structure with [pyreverse](https://pypi.org/project/pyreverse/).

![packages](/../../../../tailucas/tailucas.github.io/blob/main/assets/pylib/packages.png)

![classes](/../../../../tailucas/tailucas.github.io/blob/main/assets/pylib/comms_classes.png)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

Technologies that help make this package useful:

[![1Password][1p-shield]][1p-url]
[![Amazon AWS][aws-shield]][aws-url]
[![Poetry][poetry-shield]][poetry-url]
[![Python][python-shield]][python-url]
[![RabbitMQ][rabbit-shield]][rabbit-url]
[![Sentry][sentry-shield]][sentry-url]
[![ZeroMQ][zmq-shield]][zmq-url]

Also:

* [Cronitor][cronitor-url]
* [MessagePack][msgpack-url]

![GitHub](https://img.shields.io/static/v1?style=for-the-badge&message=GitHub&color=181717&logo=GitHub&logoColor=FFFFFF&label=)

* [Botoflow][botoflow-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

Here is some detail about the intended use of this package.

### Prerequisites

A [Python][python-url] project or runtime environment. Since this project is already initialized with [Poetry][poetry-url] dependency management, I recommend that you continue to use it. Beyond the Python dependencies defined in the [Poetry configuration](pyproject.toml), the package init carries hardcoded dependencies on [Sentry][sentry-url] and [1Password][1p-url] in order to function. Unless you want these and are effectively extending my [base project][baseapp-url], you're likely better off forking this package and cutting out what you do not need.

### Installation

This project is intended to be used as a [Git submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules) because it is not yet structured or built to be vended from the [Python Package Index](https://pypi.org/). One of my [companion projects][baseapp-url] illustrates [how easily](https://github.com/tailucas/base-app/blob/723bbef3a4f5380d722dae52bcb52537b4e44bc1/pyproject.toml#L16) the project can be added to the dependency closure of a project using Poetry which also greatly diminished the need to publish to online package indexes.

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

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2Ftailucas%2Fpylib%2F&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=visits&edge_flat=true)](https://hits.seeyoufarm.com)

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
[poetry-url]: https://python-poetry.org/
[poetry-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=Poetry&color=60A5FA&logo=Poetry&logoColor=FFFFFF&label=
[python-url]: https://www.python.org/
[python-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=Python&color=3776AB&logo=Python&logoColor=FFFFFF&label=
[rabbit-url]: https://www.rabbitmq.com/
[rabbit-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=RabbitMQ&color=FF6600&logo=RabbitMQ&logoColor=FFFFFF&label=
[sentry-url]: https://sentry.io/
[sentry-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=Sentry&color=362D59&logo=Sentry&logoColor=FFFFFF&label=
[zmq-url]: https://zeromq.org/
[zmq-shield]: https://img.shields.io/static/v1?style=for-the-badge&message=ZeroMQ&color=DF0000&logo=ZeroMQ&logoColor=FFFFFF&label=
