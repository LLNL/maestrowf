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

## Why Should You Care?
----

Stub
