

## Motivations and Goals
----

The primary goal of Maestro is to provide a lightweight tool for encouraging modularized workflow composition, a mental framework for thinking about these concepts, and a tool that users can flexibly utilize for a wide variety of use cases (science, software testing/deployment, and etc.). Maestro's vision aims to make steady progression towards making reproducible workflows user-friendly and easy to manage. We maintain a few high level principles:

1. Reproducibility is not free, nor is there a silver bullet to achieve it. It is a mixture of tooling, infrastructure, and best practices.
2. Workflow best practices should always be encouraged wherever possible, and enforced where reasonable.
3. It is not a workflow framework's place to force a user to use specific technologies -- a framework should couple minimally, but offer a high degree of flexibility.
4. Division of responsibility is critical. Data management, optimal performance, and orchestration are related but separate.
5. A workflow should be coherent and easy to communicate, with a framework sproviding users a mental framework to think and discuss such challenges.

We firmly believe that a user-friendly tool and environment that promotes provenance and best practices, while minimizing the effort needed for users to achieve progress, will greatly improve the quality of computational science.

<br/>
## What are Workflows?
----

Before we can discuss how Maestro can help you, we must first cover the most basic question: what are workflows? There are many definitions of workflow, so we try to keep it simple and define the term as follows:

``` text
A set of high level tasks to be executed in some order, with or without dependencies on each other.
```
<br/>
You may not realized it, but you are surrounded by workflows! Everything from daily activities to recipes to the commands you run in a terminal can be broken down into a set of focused steps that have dependencies on one another. For example, you can't make bread without first mixing in the dough, *then* letting it rest, and *then* mixing in the yeast. Similarly, if you're running computational simulations, your workflow might look like: set up simulation inputs, *then* simulate, *then* post process results. Both of these lists are describing processes as a set of intent-driven steps and say nothing about implementation. As our analogy exposes, there are different perspectives of workflow as follows:

* *_Intent_:* The high level objective(s) that a step is defined to accomplish at a human understandable level, removed from details such as code and tools
* *_Implementation_:* The technical details such as tool or code choice, and other specifics about how to technically execute a step

<br/>

???+ example "An Example of Intent and Implementation"
    Let's start with the recipe for baking. The steps for baking bread are roughly as follows:

    1. Mix flour and water
    2. Mix in the yeast
    3. Fold the dough
    4. Proof the dough

    Now, these steps are the procedural *intent* of achieving bread, not the implementation for how to create bread. For example, achieving a mixture of flour and water can be done in a few ways:

    - Manual mixing with your hands in a bowl
    - Mixing the flour and water with a whisk
    - Using a standing mixer with a dough hook

    All of these are *implementations* of how to achieving mixing flour and water. Software workflows behave the same way. For example, maybe you need to run a particle simulation. The first thing that needs to be communicated is the intent to run such a simulation (perhaps of some phenomena to be studied). Now, once the intent is established, you may need a particular simulator or tools -- all of which fall under implementation just as you would have a choice to achieve mixing by hand, whisk, or mixer.

<br/>
Both of intent and implementation are important perspectives to view workflows; however, one or the other is more important depending on context. Often times, intent and implementation are conflated which makes communication of a workflow process muddied at best. Maestro aims to help researchers communicate the intent by arming them with the vocabulary to do so while also providing the ability to easily automate their work at the same time.

<br/>
## Maestro's Foundation and Core Concepts
----

Maestro pulls its core concepts for executing computational workflows in an analogous fashion to what an experimentalist performs at a laboratory bench. [High performance computational resources](https://en.wikipedia.org/wiki/Supercomputer) are primarily focused on *studying* natural phenomena via [simulation (mathematical modeling)](https://en.wikipedia.org/wiki/Computer_simulation), and therefore follow a similar thought pattern. At the highest level, an experimentalist is responsible for the following:

1. Establishing, documenting, and communicating processes for running experiments
2. Running experiments over multiple parameters consistently
3. Repeating experiments on new and existing parameters

### Maestro Studies

We have designed Maestro around the core concept of what we call a "study". A study is defined as a set of steps that are executed (a workflow) over a set of parameters. A study in Maestro's context is analogous to an actual tangible scientific experiment, which has a set of clearly defined and repeatable steps which are repeated over multiple specimen.

Maestro is designed around the principles of self-documentation, consistency, and repeatability.

![Reproducibility, the intersections of documentation, consistency, & repeatability](./assets/images/reproducibility_venn.svg){: height="45%" width="45%" align=left}
#### Repeatability

Studies should be easily repeatable. Like any well-planned and implemented science experiment, a process should be run exact;y the same way each time for each parameter or over different runs of the study itself.

#### Consistent

Studies should be run in a consistent fashion. The removal of variation in the process means less mistakes when executing studies, ease of sharing with others, and uniformity in defining new studies.

#### Self-documenting

Documentation is critical in studies. The Maestro YAML Specification is an artifact documenting a complete workflow.
