---
title: awms
parent: Features
layout: page
grand_parent: Dev Containers
---

This feature includes a collection of tools and scripts designed to make it easier to configure Jupyter Hub on your local environment.

### Usage

```json
{
    "features": {
        ...
		"ghcr.io/lsc-sde/devcontainer-features/jupyterhub:latest" : {}
    }
}
```

### Options

| Name | Description | Default Value |
| --- | --- | --- |

### CLI Commands
The following scripts are provided by this feature:

#### setup jupyterhub
The ***setup jupyterhub*** command will install and configure Jupyter Hub on the local machine

Example usage:
```bash
krapctl setup jupyterhub
```

