![Maestro Logo](./assets/logo_full.png)

----

[On GitHub :fontawesome-brands-github:](https://github.com/LLNL/maestrowf){: .md-button .md-button--primary }

----

## What is Maestro?

Maestro is an open-source HPC software tool that defines a YAML-based study specification for defining multistep workflows and automates execution of software flows on HPC resources. The core design tenants of Maestro focus on encouraging clear workflow communication and documentation, while making consistent execution easier to allow users to focus on science. Maestro's study specification helps users think about complex workflows in a step-wise, intent-oriented, manner that encourages modularity and tool reuse. These principles are becoming increasingly important as computational science is continuously more present in scientific fields and has started to require a similar rigor to physical experiment. Maestro is currently in use for multiple projects at Lawrence Livermore National Laboratory and has been used to run existing codes including MFEM, and other simulation codes. It has also been used in other areas including in the training of machine-learned models and more.

----------------

## Why was Maestro Created?
----

Stub

----------------

## Motivations and Goals
----

The primary goal of Maestro is to provide a lightweight tool for encouraging modularized workflow composition, a mental framework for thinking about these concepts, and a tool that users can flexibly utilize for a wide variety of use cases (science, software testing/deployment, and etc.). Maestro's vision aims to make steady progression towards making reproducible workflows user-friendly and easy to manage. We maintain a few high level principles:

1. Reproducibility is not free, nor is there a silver bullet to achieve it. It is a mixture of tooling, infrastructure, and best practices.
2. Workflow best practices should always be encouraged wherever possible, and enforced where reasonable.
3. It is not a workflow framework's place to force a user to use specific technologies -- a framework should couple minimally, but offer a high degree of flexibility.
4. Division of responsibility is critical. Data management, optimal performance, and orchestration are related but separate.
5. A workflow should be coherent and easy to communicate, with a framework sproviding users a mental framework to think and discuss such challenges.

We firmly believe that a user-friendly tool and environment that promotes provenance and best practices, while minimizing the effort needed for users to achieve progress, will greatly improve the quality of computational science.
